"""
02_load_to_oracle.py
자동차 부품 공급망 이상 탐지 시스템 - Oracle DB 적재 스크립트

전처리된 CSV를 Oracle DB(Docker)에 적재합니다.
- suppliers  테이블: 공급업체 그룹 데이터
- orders     테이블: 주문 데이터
- 테이블이 없으면 자동 생성, 중복 방지(MERGE) 처리
"""

import oracledb
import pandas as pd
import logging
import sys
from pathlib import Path

# ── 로깅 설정 ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)

# ── 경로 / 접속 설정 ───────────────────────────────────────────────────────────
BASE_DIR    = Path.home() / "scm_portfolio"
PROC_DIR    = BASE_DIR / "data" / "processed"

DB_USER     = "scm_user"
DB_PASSWORD = "scm1234"
DB_HOST     = "localhost"
DB_PORT     = 1521
DB_SERVICE  = "FREEPDB1"
DSN         = f"{DB_HOST}:{DB_PORT}/{DB_SERVICE}"

# 한 번에 INSERT할 배치 크기
BATCH_SIZE  = 500


# ══════════════════════════════════════════════════════════════════════════════
# DDL: 테이블 생성 SQL
# ══════════════════════════════════════════════════════════════════════════════
DDL_SUPPLIERS = """
CREATE TABLE suppliers (
    supplier_id     NUMBER          PRIMARY KEY,
    market          VARCHAR2(100),
    order_region    VARCHAR2(100),
    shipping_mode   VARCHAR2(50),
    total_orders    NUMBER,
    avg_delay_days  NUMBER(10, 2),
    late_rate       NUMBER(6, 2),
    avg_quantity    NUMBER(10, 2),
    created_at      DATE DEFAULT SYSDATE
)
"""

DDL_ORDERS = """
CREATE TABLE orders (
    order_id            NUMBER          PRIMARY KEY,
    supplier_id         NUMBER,
    order_date          DATE,
    ship_date           DATE,
    ship_days_real      NUMBER,
    ship_days_sched     NUMBER,
    delay_days          NUMBER(10, 2),
    is_delayed          NUMBER(1),
    late_delivery_risk  NUMBER(1),
    delivery_status     VARCHAR2(50),
    order_status        VARCHAR2(50),
    quantity            NUMBER,
    discount_rate       NUMBER(8, 4),
    profit_ratio        NUMBER(8, 4),
    product_name        VARCHAR2(200),
    category_name       VARCHAR2(100),
    market              VARCHAR2(100),
    order_region        VARCHAR2(100),
    shipping_mode       VARCHAR2(50),
    order_year          NUMBER(4),
    order_month         NUMBER(2),
    created_at          DATE DEFAULT SYSDATE,
    CONSTRAINT fk_supplier FOREIGN KEY (supplier_id)
        REFERENCES suppliers(supplier_id)
)
"""

DDL_ANOMALY_RESULTS = """
CREATE TABLE anomaly_results (
    result_id       NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    order_id        NUMBER,
    anomaly_score   NUMBER(10, 6),
    is_anomaly      NUMBER(1),
    risk_level      VARCHAR2(10),
    delay_days      NUMBER(10, 2),
    quantity        NUMBER,
    discount_rate   NUMBER(8, 4),
    profit_ratio    NUMBER(8, 4),
    detected_at     DATE DEFAULT SYSDATE,
    CONSTRAINT fk_order FOREIGN KEY (order_id)
        REFERENCES orders(order_id)
)
"""


# ══════════════════════════════════════════════════════════════════════════════
# 유틸: 테이블 존재 여부 확인 및 생성
# ══════════════════════════════════════════════════════════════════════════════
def ensure_table(conn: oracledb.Connection, table_name: str, ddl: str) -> None:
    """테이블이 없으면 생성한다."""
    cursor = conn.cursor()
    cursor.execute(
        "SELECT COUNT(*) FROM user_tables WHERE table_name = :1",
        [table_name.upper()],
    )
    exists = cursor.fetchone()[0]
    if not exists:
        log.info(f"테이블 생성: {table_name}")
        cursor.execute(ddl)
        conn.commit()
    else:
        log.info(f"테이블 이미 존재: {table_name}")
    cursor.close()


def get_row_count(conn: oracledb.Connection, table_name: str) -> int:
    cursor = conn.cursor()
    cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
    count = cursor.fetchone()[0]
    cursor.close()
    return count


# ══════════════════════════════════════════════════════════════════════════════
# suppliers 적재 (MERGE로 중복 방지)
# ══════════════════════════════════════════════════════════════════════════════
MERGE_SUPPLIER = """
MERGE INTO suppliers tgt
USING (
    SELECT :supplier_id     AS supplier_id,
           :market          AS market,
           :order_region    AS order_region,
           :shipping_mode   AS shipping_mode,
           :total_orders    AS total_orders,
           :avg_delay_days  AS avg_delay_days,
           :late_rate       AS late_rate,
           :avg_quantity    AS avg_quantity
    FROM dual
) src
ON (tgt.supplier_id = src.supplier_id)
WHEN MATCHED THEN UPDATE SET
    tgt.total_orders   = src.total_orders,
    tgt.avg_delay_days = src.avg_delay_days,
    tgt.late_rate      = src.late_rate,
    tgt.avg_quantity   = src.avg_quantity
WHEN NOT MATCHED THEN INSERT (
    supplier_id, market, order_region, shipping_mode,
    total_orders, avg_delay_days, late_rate, avg_quantity
) VALUES (
    src.supplier_id, src.market, src.order_region, src.shipping_mode,
    src.total_orders, src.avg_delay_days, src.late_rate, src.avg_quantity
)
"""


def load_suppliers(conn: oracledb.Connection, df: pd.DataFrame) -> None:
    log.info(f"suppliers 적재 시작: {len(df):,}건")
    cursor = conn.cursor()

    rows = [
        {
            "supplier_id":    int(r.supplier_id),
            "market":         str(r.market)[:100],
            "order_region":   str(r.order_region)[:100],
            "shipping_mode":  str(r.shipping_mode)[:50],
            "total_orders":   int(r.total_orders),
            "avg_delay_days": float(r.avg_delay_days),
            "late_rate":      float(r.late_rate),
            "avg_quantity":   float(r.avg_quantity),
        }
        for r in df.itertuples(index=False)
    ]

    inserted = updated = 0
    for i in range(0, len(rows), BATCH_SIZE):
        batch = rows[i : i + BATCH_SIZE]
        cursor.executemany(MERGE_SUPPLIER, batch)
        conn.commit()
        inserted += len(batch)
        log.info(f"  suppliers: {inserted:,}/{len(rows):,} 처리 완료")

    cursor.close()
    log.info(f"suppliers 적재 완료. DB 총 {get_row_count(conn, 'suppliers'):,}건")


# ══════════════════════════════════════════════════════════════════════════════
# orders 적재 (MERGE로 중복 방지)
# ══════════════════════════════════════════════════════════════════════════════
MERGE_ORDER = """
MERGE INTO orders tgt
USING (
    SELECT :order_id           AS order_id,
           :supplier_id        AS supplier_id,
           TO_DATE(:order_date, 'YYYY-MM-DD') AS order_date,
           TO_DATE(:ship_date,  'YYYY-MM-DD') AS ship_date,
           :ship_days_real     AS ship_days_real,
           :ship_days_sched    AS ship_days_sched,
           :delay_days         AS delay_days,
           :is_delayed         AS is_delayed,
           :late_delivery_risk AS late_delivery_risk,
           :delivery_status    AS delivery_status,
           :order_status       AS order_status,
           :quantity           AS quantity,
           :discount_rate      AS discount_rate,
           :profit_ratio       AS profit_ratio,
           :product_name       AS product_name,
           :category_name      AS category_name,
           :market             AS market,
           :order_region       AS order_region,
           :shipping_mode      AS shipping_mode,
           :order_year         AS order_year,
           :order_month        AS order_month
    FROM dual
) src
ON (tgt.order_id = src.order_id)
WHEN MATCHED THEN UPDATE SET
    tgt.delay_days         = src.delay_days,
    tgt.is_delayed         = src.is_delayed,
    tgt.late_delivery_risk = src.late_delivery_risk,
    tgt.delivery_status    = src.delivery_status
WHEN NOT MATCHED THEN INSERT (
    order_id, supplier_id, order_date, ship_date,
    ship_days_real, ship_days_sched, delay_days, is_delayed,
    late_delivery_risk, delivery_status, order_status,
    quantity, discount_rate, profit_ratio,
    product_name, category_name,
    market, order_region, shipping_mode,
    order_year, order_month
) VALUES (
    src.order_id, src.supplier_id, src.order_date, src.ship_date,
    src.ship_days_real, src.ship_days_sched, src.delay_days, src.is_delayed,
    src.late_delivery_risk, src.delivery_status, src.order_status,
    src.quantity, src.discount_rate, src.profit_ratio,
    src.product_name, src.category_name,
    src.market, src.order_region, src.shipping_mode,
    src.order_year, src.order_month
)
"""


def _safe_int(val, default=0):
    try:
        v = int(val)
        return v if not pd.isna(val) else default
    except Exception:
        return default


def _safe_float(val, default=0.0):
    try:
        v = float(val)
        return v if not pd.isna(val) else default
    except Exception:
        return default


def _safe_str(val, maxlen=200):
    return str(val)[:maxlen] if pd.notna(val) else ""


def load_orders(conn: oracledb.Connection, df: pd.DataFrame) -> None:
    log.info(f"orders 적재 시작: {len(df):,}건")
    cursor = conn.cursor()

    rows = [
        {
            "order_id":           _safe_int(r.order_id),
            "supplier_id":        _safe_int(r.supplier_id),
            "order_date":         str(r.order_date_str) if hasattr(r, "order_date_str") else str(r.order_date)[:10],
            "ship_date":          str(r.ship_date_str)  if hasattr(r, "ship_date_str")  else str(r.ship_date)[:10],
            "ship_days_real":     _safe_float(r.ship_days_real),
            "ship_days_sched":    _safe_float(r.ship_days_sched),
            "delay_days":         _safe_float(r.delay_days),
            "is_delayed":         _safe_int(r.is_delayed),
            "late_delivery_risk": _safe_int(r.late_delivery_risk),
            "delivery_status":    _safe_str(r.delivery_status, 50),
            "order_status":       _safe_str(r.order_status, 50),
            "quantity":           _safe_int(r.quantity),
            "discount_rate":      _safe_float(r.discount_rate),
            "profit_ratio":       _safe_float(r.profit_ratio),
            "product_name":       _safe_str(r.product_name, 200),
            "category_name":      _safe_str(r.category_name, 100),
            "market":             _safe_str(r.market, 100),
            "order_region":       _safe_str(r.order_region, 100),
            "shipping_mode":      _safe_str(r.shipping_mode, 50),
            "order_year":         _safe_int(r.order_year),
            "order_month":        _safe_int(r.order_month),
        }
        for r in df.itertuples(index=False)
    ]

    total = len(rows)
    for i in range(0, total, BATCH_SIZE):
        batch = rows[i : i + BATCH_SIZE]
        cursor.executemany(MERGE_ORDER, batch)
        conn.commit()
        log.info(f"  orders: {min(i + BATCH_SIZE, total):,}/{total:,} 처리 완료")

    cursor.close()
    log.info(f"orders 적재 완료. DB 총 {get_row_count(conn, 'orders'):,}건")


# ══════════════════════════════════════════════════════════════════════════════
# Main
# ══════════════════════════════════════════════════════════════════════════════
def main():
    log.info("=" * 60)
    log.info("Oracle DB 적재 시작")
    log.info(f"접속: {DB_USER}@{DSN}")
    log.info("=" * 60)

    # ── CSV 로드 ──────────────────────────────────────────────────────────────
    sup_path = PROC_DIR / "suppliers_clean.csv"
    ord_path = PROC_DIR / "orders_clean.csv"

    if not sup_path.exists() or not ord_path.exists():
        log.error("전처리된 CSV 파일이 없습니다. 먼저 01_preprocess.py를 실행하세요.")
        sys.exit(1)

    suppliers_df = pd.read_csv(sup_path)
    orders_df    = pd.read_csv(ord_path)
    log.info(f"CSV 로드: suppliers {len(suppliers_df):,}행, orders {len(orders_df):,}행")

    # ── DB 연결 ───────────────────────────────────────────────────────────────
    try:
        conn = oracledb.connect(
            user=DB_USER,
            password=DB_PASSWORD,
            dsn=DSN,
        )
        log.info("Oracle DB 연결 성공")
    except oracledb.DatabaseError as e:
        log.error(f"DB 연결 실패: {e}")
        log.error("Docker Oracle 컨테이너가 실행 중인지 확인하세요.")
        sys.exit(1)

    try:
        # ── 테이블 생성 (없으면) ──────────────────────────────────────────────
        ensure_table(conn, "suppliers",      DDL_SUPPLIERS)
        ensure_table(conn, "orders",         DDL_ORDERS)
        ensure_table(conn, "anomaly_results", DDL_ANOMALY_RESULTS)

        # ── 데이터 적재 ───────────────────────────────────────────────────────
        load_suppliers(conn, suppliers_df)
        load_orders(conn, orders_df)

        log.info("-" * 60)
        log.info("[적재 요약]")
        log.info(f"  suppliers      : {get_row_count(conn, 'suppliers'):,}건")
        log.info(f"  orders         : {get_row_count(conn, 'orders'):,}건")
        log.info(f"  anomaly_results: {get_row_count(conn, 'anomaly_results'):,}건 (탐지 전)")
        log.info("Oracle DB 적재 완료 ✓")
        log.info("=" * 60)

    except Exception as e:
        log.error(f"적재 중 오류: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()
        log.info("DB 연결 종료")


if __name__ == "__main__":
    main()
