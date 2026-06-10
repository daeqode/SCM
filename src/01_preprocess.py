"""
01_preprocess.py
자동차 부품 공급망 이상 탐지 시스템 - 데이터 전처리 스크립트

DataCoSupplyChainDataset.csv를 읽어 Oracle DB 적재용으로 변환합니다.
- suppliers 테이블용 공급업체 데이터 추출
- orders 테이블용 주문 데이터 변환
- 지연일수 계산 컬럼 추가
"""

import pandas as pd
import numpy as np
import os
import logging
from pathlib import Path

# ── 로깅 설정 ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)

# ── 경로 설정 ──────────────────────────────────────────────────────────────────
BASE_DIR = Path.home() / "scm_portfolio"
DATA_PATH = BASE_DIR / "data" / "DataCoSupplyChainDataset.csv"
OUTPUT_DIR = BASE_DIR / "data" / "processed"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ── 사용할 컬럼 정의 ───────────────────────────────────────────────────────────
REQUIRED_COLUMNS = [
    "Order Id",
    "order date (DateOrders)",
    "shipping date (DateOrders)",
    "Days for shipping (real)",
    "Days for shipment (scheduled)",
    "Late_delivery_risk",
    "Delivery Status",
    "Order Item Quantity",
    "Order Item Discount Rate",
    "Order Item Profit Ratio",
    "Product Name",
    "Category Name",
    "Market",
    "Order Region",
    "Order Status",
    "Shipping Mode",
    "Customer Id",
    "Customer Segment",
]


# ══════════════════════════════════════════════════════════════════════════════
# 1. 데이터 로드
# ══════════════════════════════════════════════════════════════════════════════
def load_data(path: Path) -> pd.DataFrame:
    log.info(f"데이터 로드 중: {path}")
    # DataCo 데이터셋은 latin-1 인코딩 사용
    df = pd.read_csv(path, encoding="latin-1", low_memory=False)
    log.info(f"원본 데이터: {df.shape[0]:,}행 × {df.shape[1]}컬럼")
    return df


# ══════════════════════════════════════════════════════════════════════════════
# 2. 필요한 컬럼 선택
# ══════════════════════════════════════════════════════════════════════════════
def select_columns(df: pd.DataFrame) -> pd.DataFrame:
    available = [c for c in REQUIRED_COLUMNS if c in df.columns]
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        log.warning(f"없는 컬럼 (무시): {missing}")
    df = df[available].copy()
    log.info(f"컬럼 선택 후: {df.shape[1]}개 컬럼")
    return df


# ══════════════════════════════════════════════════════════════════════════════
# 3. 컬럼명 정리 (공백·괄호 제거 → snake_case)
# ══════════════════════════════════════════════════════════════════════════════
def rename_columns(df: pd.DataFrame) -> pd.DataFrame:
    rename_map = {
        "Order Id":                        "order_id",
        "order date (DateOrders)":         "order_date",
        "shipping date (DateOrders)":      "ship_date",
        "Days for shipping (real)":        "ship_days_real",
        "Days for shipment (scheduled)":   "ship_days_sched",
        "Late_delivery_risk":              "late_delivery_risk",
        "Delivery Status":                 "delivery_status",
        "Order Item Quantity":             "quantity",
        "Order Item Discount Rate":        "discount_rate",
        "Order Item Profit Ratio":         "profit_ratio",
        "Product Name":                    "product_name",
        "Category Name":                   "category_name",
        "Market":                          "market",
        "Order Region":                    "order_region",
        "Order Status":                    "order_status",
        "Shipping Mode":                   "shipping_mode",
        "Customer Id":                     "customer_id",
        "Customer Segment":                "customer_segment",
    }
    df = df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})
    return df


# ══════════════════════════════════════════════════════════════════════════════
# 4. 결측치 처리
# ══════════════════════════════════════════════════════════════════════════════
def handle_missing(df: pd.DataFrame) -> pd.DataFrame:
    before = len(df)

    # 핵심 컬럼(주문ID, 날짜, 배송일수)이 없는 행 제거
    critical = ["order_id", "order_date", "ship_date",
                "ship_days_real", "ship_days_sched"]
    critical_existing = [c for c in critical if c in df.columns]
    df = df.dropna(subset=critical_existing)

    # 수치형 결측 → 중앙값 대체
    for col in ["quantity", "discount_rate", "profit_ratio"]:
        if col in df.columns:
            median_val = df[col].median()
            df[col] = df[col].fillna(median_val)

    # 범주형 결측 → 'Unknown'
    for col in ["delivery_status", "order_status", "shipping_mode",
                "product_name", "category_name", "market",
                "order_region", "customer_segment"]:
        if col in df.columns:
            df[col] = df[col].fillna("Unknown")

    after = len(df)
    log.info(f"결측치 처리: {before - after:,}행 제거 → {after:,}행 남음")
    return df


# ══════════════════════════════════════════════════════════════════════════════
# 5. 날짜 형식 변환
# ══════════════════════════════════════════════════════════════════════════════
def parse_dates(df: pd.DataFrame) -> pd.DataFrame:
    for col in ["order_date", "ship_date"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], infer_datetime_format=True, errors="coerce")
    # 날짜 파싱 실패한 행 제거
    before = len(df)
    df = df.dropna(subset=["order_date", "ship_date"])
    removed = before - len(df)
    if removed:
        log.warning(f"날짜 파싱 실패로 {removed}행 제거")
    log.info("날짜 변환 완료")
    return df


# ══════════════════════════════════════════════════════════════════════════════
# 6. 파생 컬럼 추가
# ══════════════════════════════════════════════════════════════════════════════
def add_derived_columns(df: pd.DataFrame) -> pd.DataFrame:
    # 지연일수: 실제 배송일 - 예정 배송일 (양수 = 지연, 음수 = 조기 도착)
    if "ship_days_real" in df.columns and "ship_days_sched" in df.columns:
        df["delay_days"] = df["ship_days_real"] - df["ship_days_sched"]

    # 지연 여부 플래그
    df["is_delayed"] = (df["delay_days"] > 0).astype(int)

    # 주문 연도/월 (시계열 분석용)
    if "order_date" in df.columns:
        df["order_year"]  = df["order_date"].dt.year
        df["order_month"] = df["order_date"].dt.month

    log.info("파생 컬럼 추가: delay_days, is_delayed, order_year, order_month")
    return df


# ══════════════════════════════════════════════════════════════════════════════
# 7. suppliers 테이블용 데이터 추출
#    (Market + Order Region + Shipping Mode 조합을 공급업체 그룹으로 간주)
# ══════════════════════════════════════════════════════════════════════════════
def build_suppliers(df: pd.DataFrame) -> pd.DataFrame:
    log.info("suppliers 테이블 데이터 생성 중...")

    # 공급업체를 'Market | Order Region | Shipping Mode' 조합으로 정의
    grp = df.groupby(["market", "order_region", "shipping_mode"], dropna=False)

    suppliers = grp.agg(
        total_orders=("order_id",      "count"),
        avg_delay_days=("delay_days",  "mean"),
        late_rate=("is_delayed",       "mean"),   # 지연율 (0~1)
        avg_quantity=("quantity",       "mean"),
    ).reset_index()

    # 고유 supplier_id 부여
    suppliers.insert(0, "supplier_id", range(1, len(suppliers) + 1))

    # 컬럼 정리
    suppliers["avg_delay_days"] = suppliers["avg_delay_days"].round(2)
    suppliers["late_rate"]      = (suppliers["late_rate"] * 100).round(2)   # %
    suppliers["avg_quantity"]   = suppliers["avg_quantity"].round(2)

    log.info(f"suppliers 레코드 수: {len(suppliers):,}")
    return suppliers


# ══════════════════════════════════════════════════════════════════════════════
# 8. orders 테이블용 데이터 변환
# ══════════════════════════════════════════════════════════════════════════════
def build_orders(df: pd.DataFrame, suppliers: pd.DataFrame) -> pd.DataFrame:
    log.info("orders 테이블 데이터 생성 중...")

    # suppliers의 supplier_id를 orders에 조인
    orders = df.merge(
        suppliers[["supplier_id", "market", "order_region", "shipping_mode"]],
        on=["market", "order_region", "shipping_mode"],
        how="left",
    )

    # Oracle DATE 호환 포맷으로 변환 (문자열)
    orders["order_date_str"] = orders["order_date"].dt.strftime("%Y-%m-%d")
    orders["ship_date_str"]  = orders["ship_date"].dt.strftime("%Y-%m-%d")

    # 최종 orders 컬럼 선택
    order_cols = [
        "order_id", "supplier_id",
        "order_date_str", "ship_date_str",
        "ship_days_real", "ship_days_sched", "delay_days", "is_delayed",
        "late_delivery_risk", "delivery_status", "order_status",
        "quantity", "discount_rate", "profit_ratio",
        "product_name", "category_name",
        "market", "order_region", "shipping_mode",
        "order_year", "order_month",
    ]
    order_cols_exist = [c for c in order_cols if c in orders.columns]
    orders = orders[order_cols_exist].copy()

    # order_id 중복 제거 (동일 주문에 다중 아이템이 있을 경우 첫 번째 유지)
    before = len(orders)
    orders = orders.drop_duplicates(subset=["order_id"], keep="first")
    log.info(f"order_id 중복 제거: {before - len(orders):,}행 → {len(orders):,}행 남음")

    return orders


# ══════════════════════════════════════════════════════════════════════════════
# 9. 결과 저장 (CSV)
# ══════════════════════════════════════════════════════════════════════════════
def save_outputs(suppliers: pd.DataFrame, orders: pd.DataFrame) -> None:
    sup_path = OUTPUT_DIR / "suppliers_clean.csv"
    ord_path = OUTPUT_DIR / "orders_clean.csv"

    suppliers.to_csv(sup_path, index=False, encoding="utf-8-sig")
    orders.to_csv(ord_path,   index=False, encoding="utf-8-sig")

    log.info(f"저장 완료:")
    log.info(f"  suppliers → {sup_path}  ({len(suppliers):,}행)")
    log.info(f"  orders    → {ord_path}  ({len(orders):,}행)")


# ══════════════════════════════════════════════════════════════════════════════
# Main
# ══════════════════════════════════════════════════════════════════════════════
def main():
    log.info("=" * 60)
    log.info("SCM 데이터 전처리 시작")
    log.info("=" * 60)

    # 1~6 단계: 원본 데이터 → 정제된 DataFrame
    df = load_data(DATA_PATH)
    df = select_columns(df)
    df = rename_columns(df)
    df = handle_missing(df)
    df = parse_dates(df)
    df = add_derived_columns(df)

    # 7~8 단계: 테이블별 데이터 생성
    suppliers = build_suppliers(df)
    orders    = build_orders(df, suppliers)

    # 9 단계: 저장
    save_outputs(suppliers, orders)

    # 간단한 요약 출력
    log.info("-" * 60)
    log.info("[전처리 요약]")
    log.info(f"  처리된 주문 수   : {len(orders):,}건")
    log.info(f"  공급업체 그룹 수 : {len(suppliers):,}개")
    log.info(f"  전체 지연율      : {orders['is_delayed'].mean() * 100:.1f}%")
    log.info(f"  평균 지연일수    : {orders['delay_days'].mean():.2f}일")
    log.info("전처리 완료 ✓")
    log.info("=" * 60)

    return suppliers, orders


if __name__ == "__main__":
    main()
