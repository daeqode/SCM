import oracledb
import pandas as pd
import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
import logging
from collections import Counter

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)

DB_USER = "scm_user"
DB_PASS = "scm1234"
DB_DSN  = "localhost:1521/FREEPDB1"

FEATURE_COLS = ["delay_days", "quantity", "discount_rate", "profit_ratio"]

def main():
    log.info("=" * 60)
    log.info("Isolation Forest 이상탐지 시작")
    log.info("=" * 60)

    conn = oracledb.connect(user=DB_USER, password=DB_PASS, dsn=DB_DSN)
    log.info("Oracle DB 연결 성공")

    # 데이터 로드
    log.info("orders 테이블 로드 중...")
    cursor = conn.cursor()
    cursor.execute("SELECT order_id, delay_days, quantity, discount_rate, profit_ratio FROM orders")
    rows = cursor.fetchall()
    df = pd.DataFrame(rows, columns=["order_id","delay_days","quantity","discount_rate","profit_ratio"])
    log.info(f"orders 로드 완료: {len(df):,}건")

    # 피처 준비
    X = df[FEATURE_COLS].fillna(0).values

    # 정규화
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    log.info(f"피처 정규화 완료: {X_scaled.shape}")

    # 모델 학습
    log.info("Isolation Forest 학습 중 (n_estimators=200, contamination=0.05) ...")
    model = IsolationForest(n_estimators=200, contamination=0.05, random_state=42)
    predictions = model.fit_predict(X_scaled)
    scores = model.decision_function(X_scaled)

    # 이상 탐지 결과
    n_anomaly = (predictions == -1).sum()
    log.info(f"탐지 완료: 이상 {n_anomaly:,}건 ({n_anomaly/len(df)*100:.1f}%)")

    # 리스크 분류
    def classify_risk(pred, score):
        if pred == 1:
            return "NORMAL"
        if score < -0.15:
            return "HIGH"
        elif score < -0.08:
            return "MEDIUM"
        else:
            return "LOW"

    risk_levels = [classify_risk(p, s) for p, s in zip(predictions, scores)]
    cnt = Counter(risk_levels)
    log.info(f"리스크 분류 — HIGH: {cnt['HIGH']}건 | MEDIUM: {cnt['MEDIUM']}건 | LOW: {cnt['LOW']}건 | NORMAL: {cnt['NORMAL']}건")

    # anomaly_results 저장
    log.info("anomaly_results 저장 중...")
    cursor.execute("DELETE FROM anomaly_results")

    insert_sql = """
    INSERT INTO anomaly_results
        (order_id, risk_level, anomaly_score, is_anomaly,
         delay_days, quantity, discount_rate, profit_ratio)
    VALUES
        (:1, :2, :3, :4, :5, :6, :7, :8)
    """

    batch = []
    for i in range(len(df)):
        if predictions[i] == -1:
            batch.append((
                str(df["order_id"].iloc[i]),
                risk_levels[i],
                float(scores[i]),
                1,
                float(df["delay_days"].iloc[i]) if pd.notna(df["delay_days"].iloc[i]) else 0.0,
                float(df["quantity"].iloc[i]) if pd.notna(df["quantity"].iloc[i]) else 0.0,
                float(df["discount_rate"].iloc[i]) if pd.notna(df["discount_rate"].iloc[i]) else 0.0,
                float(df["profit_ratio"].iloc[i]) if pd.notna(df["profit_ratio"].iloc[i]) else 0.0,
            ))

    cursor.executemany(insert_sql, batch)
    conn.commit()
    log.info(f"anomaly_results 저장 완료: {len(batch):,}건")

    cursor.close()
    conn.close()
    log.info("DB 연결 종료")
    log.info("이상탐지 완료 ✓")
    log.info("=" * 60)

if __name__ == "__main__":
    main()
