# 🔍 자동차 부품 공급망 이상 탐지 시스템
# SCM Anomaly Detection System

<br>

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![Oracle](https://img.shields.io/badge/Oracle-23ai_Free-F80000?style=flat-square&logo=oracle&logoColor=white)](https://www.oracle.com/database/free/)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?style=flat-square&logo=docker&logoColor=white)](https://docker.com)
[![scikit-learn](https://img.shields.io/badge/scikit--learn-Isolation_Forest-F7931E?style=flat-square&logo=scikitlearn&logoColor=white)](https://scikit-learn.org)
[![Streamlit](https://img.shields.io/badge/Streamlit-Dashboard-FF4B4B?style=flat-square&logo=streamlit&logoColor=white)](https://streamlit.io)

---

## 📋 목차 / Table of Contents

- [프로젝트 개요 / Overview](#-프로젝트-개요--overview)
- [주요 결과 / Key Results](#-주요-결과--key-results)
- [기술 스택 / Tech Stack](#-기술-스택--tech-stack)
- [프로젝트 구조 / Project Structure](#-프로젝트-구조--project-structure)
- [설치 방법 / Installation](#-설치-방법--installation)
- [실행 방법 / How to Run](#-실행-방법--how-to-run)
- [데이터 파이프라인 / Data Pipeline](#-데이터-파이프라인--data-pipeline)
- [이상탐지 모델 / Anomaly Detection Model](#-이상탐지-모델--anomaly-detection-model)
- [결과 스크린샷 / Screenshots](#-결과-스크린샷--screenshots)
- [데이터셋 / Dataset](#-데이터셋--dataset)

---

## 🎯 프로젝트 개요 / Overview

### 한국어

자동차 부품 공급망에서 발생하는 **배송 지연, 비정상 주문 패턴, 리스크 공급업체**를 AI(Isolation Forest)로 자동 탐지하는 엔드-투-엔드 데이터 파이프라인 프로젝트입니다.

Kaggle의 실제 물류 데이터(180,519행)를 Oracle 23ai DB에 적재하고, 머신러닝 기반 이상탐지 결과를 Streamlit 대시보드로 시각화합니다. 이화SCM이 추진하는 **AX(AI Transformation) 기반 SCM 자동화** 업무와 직결되는 역량을 실증합니다.

### English

An end-to-end data pipeline that automatically detects **delivery delays, abnormal order patterns, and high-risk suppliers** in an automotive parts supply chain using Isolation Forest.

Real-world logistics data (180,519 rows) from Kaggle is loaded into Oracle 23ai DB, and anomaly detection results are visualized on a Streamlit dashboard. This project directly demonstrates capabilities aligned with **Ewha SCM's AX Transformation and AI-driven SCM automation** initiatives.

---

## 📊 주요 결과 / Key Results

| 지표 / Metric | 수치 / Value |
|---|---|
| 원본 데이터 행수 / Raw Data Rows | 180,519 |
| 처리된 주문 건수 / Processed Orders | 65,752 |
| 공급업체 그룹 수 / Supplier Groups | 92 |
| 전체 배송 지연율 / Overall Late Delivery Rate | **57.3%** |
| 이상 탐지 건수 / Anomalies Detected | **3,288건 (5.0%)** |
| HIGH 리스크 / HIGH Risk | 0건 |
| MEDIUM 리스크 / MEDIUM Risk | **130건** |
| LOW 리스크 / LOW Risk | **3,158건** |

> ⚠️ **57.3% 지연율은 공급망 전반의 구조적 문제를 시사합니다.**  
> A 57.3% late delivery rate signals systemic supply chain vulnerabilities.

---

## 🛠 기술 스택 / Tech Stack

| 분류 / Category | 기술 / Technology |
|---|---|
| 언어 / Language | Python 3.11+ |
| 데이터 처리 / Data Processing | pandas, numpy |
| 머신러닝 / ML | scikit-learn (Isolation Forest) |
| 데이터베이스 / Database | Oracle 23ai Free |
| DB 드라이버 / DB Driver | python-oracledb |
| 컨테이너 / Container | Docker |
| 대시보드 / Dashboard | Streamlit |
| 데이터 소스 / Data Source | Kaggle API |

---

## 📁 프로젝트 구조 / Project Structure

```
scm_portfolio/
│
├── data/
│   ├── DataCoSupplyChainDataset.csv   # 원본 데이터 (Kaggle)
│   └── processed/
│       ├── suppliers_clean.csv        # 전처리된 공급업체 데이터
│       └── orders_clean.csv           # 전처리된 주문 데이터
│
├── src/
│   ├── 01_preprocess.py               # 데이터 전처리 파이프라인
│   ├── 02_load_to_oracle.py           # Oracle DB 적재 (MERGE/Upsert)
│   ├── 03_anomaly_detection.py        # Isolation Forest 이상탐지
│   └── 04_dashboard.py                # Streamlit 대시보드
│
├── screenshots/                       # 결과 스크린샷
│
├── requirements.txt
└── README.md
```

---

## ⚙️ 설치 방법 / Installation

### 1. 저장소 클론 / Clone Repository

```bash
git clone https://github.com/<your-username>/scm_portfolio.git
cd scm_portfolio
```

### 2. Python 패키지 설치 / Install Python Packages

```bash
pip install -r requirements.txt
```

**requirements.txt**
```
pandas>=2.0
numpy>=1.24
scikit-learn>=1.3
oracledb>=1.4
streamlit>=1.30
plotly>=5.18
```

### 3. Oracle 23ai Docker 실행 / Start Oracle 23ai Docker

```bash
# Oracle 23ai Free 컨테이너 실행
docker run -d \
  --name oracle23ai \
  -p 1521:1521 \
  -e ORACLE_PASSWORD=oracle \
  container-registry.oracle.com/database/free:latest

# 컨테이너 준비 완료까지 대기 (약 2~3분)
docker logs -f oracle23ai | grep "DATABASE IS READY"
```

### 4. DB 사용자 생성 / Create DB User

```bash
docker exec -it oracle23ai sqlplus sys/oracle@FREEPDB1 as sysdba
```

```sql
CREATE USER scm_user IDENTIFIED BY scm1234;
GRANT CONNECT, RESOURCE, UNLIMITED TABLESPACE TO scm_user;
EXIT;
```

---

## ▶️ 실행 방법 / How to Run

> 반드시 순서대로 실행하세요 / Run in order

```bash
# Step 1: 데이터 전처리 / Preprocess Data
python src/01_preprocess.py

# Step 2: Oracle DB 적재 / Load to Oracle DB
python src/02_load_to_oracle.py

# Step 3: 이상탐지 실행 / Run Anomaly Detection
python src/03_anomaly_detection.py

# Step 4: 대시보드 실행 / Launch Dashboard
streamlit run src/04_dashboard.py
```

각 스크립트는 독립적으로 재실행 가능합니다 (MERGE 기반 중복 방지 처리).  
Each script is idempotent — safe to re-run (MERGE-based deduplication).

---

## 🔄 데이터 파이프라인 / Data Pipeline

```
[Kaggle CSV]
     │
     ▼
[01_preprocess.py]
  - 컬럼 선택 및 rename
  - 결측치 처리 (중앙값/Unknown)
  - 날짜 파싱
  - delay_days 파생 컬럼 생성
  - suppliers / orders 데이터 분리
     │
     ▼
[02_load_to_oracle.py]
  - suppliers 테이블 MERGE (92건)
  - orders 테이블 MERGE (65,752건)
  - anomaly_results 테이블 DDL 생성
  - 500건 배치 INSERT
     │
     ▼
[03_anomaly_detection.py]
  - Oracle에서 orders 로드
  - StandardScaler 정규화
  - Isolation Forest 학습 (n=200, contamination=5%)
  - anomaly_score 0~1 정규화
  - 리스크 레벨 분류 (HIGH/MEDIUM/LOW)
  - anomaly_results 저장 (3,288건)
     │
     ▼
[04_dashboard.py]
  - Streamlit 실시간 시각화
  - 공급업체별 지연율 차트
  - 리스크 현황 요약
  - 이상탐지 결과 테이블
```

---

## 🤖 이상탐지 모델 / Anomaly Detection Model

### Isolation Forest

비지도 학습 기반 이상탐지 알고리즘으로, 정상 데이터보다 이상 데이터가 **더 적은 분기**로 격리되는 원리를 활용합니다.

An unsupervised anomaly detection algorithm that isolates anomalies using **fewer splits** than normal data points.

**사용 피처 / Features Used**

| 피처 / Feature | 설명 / Description |
|---|---|
| `delay_days` | 실제 배송일 − 예정 배송일 (지연일수) |
| `quantity` | 주문 수량 |
| `discount_rate` | 할인율 |
| `profit_ratio` | 이익률 |

**모델 파라미터 / Model Parameters**

```python
IsolationForest(
    n_estimators=200,      # 트리 개수 (기본 100보다 높여 안정성 향상)
    contamination=0.05,    # 이상치 비율 가정 5%
    random_state=42,
    n_jobs=-1              # 멀티코어 병렬 처리
)
```

**리스크 레벨 분류 기준 / Risk Level Classification**

| 레벨 / Level | 기준 / Criteria | 건수 / Count |
|---|---|---|
| `HIGH` | 이상치 중 anomaly_score 상위 5% | 0건 |
| `MEDIUM` | 이상치 중 anomaly_score 상위 6~20% | 130건 |
| `LOW` | 나머지 이상치 | 3,158건 |
| `NORMAL` | 정상 주문 | 62,464건 |

---

## 📸 결과 스크린샷 / Screenshots

> 스크린샷은 `screenshots/` 폴더에 추가 예정입니다.  
> Screenshots will be added to the `screenshots/` directory.

| 화면 / Screen | 설명 / Description |
|---|---|
| `01_preprocess_output.png` | 전처리 실행 로그 |
| `02_oracle_load_output.png` | DB 적재 완료 로그 |
| `03_anomaly_output.png` | 이상탐지 분석 리포트 |
| `04_dashboard.png` | Streamlit 대시보드 전체 화면 |

---

## 📦 데이터셋 / Dataset

**DataCo Smart Supply Chain Dataset**  
- 출처 / Source: [Kaggle — DataCo Supply Chain Dataset](https://www.kaggle.com/datasets/shashwatwork/dataco-smart-supply-chain-for-big-data-analysis)
- 규모 / Size: 180,519행 × 53컬럼
- 라이선스 / License: CC BY 4.0

```bash
# Kaggle API로 다운로드 / Download via Kaggle API
kaggle datasets download -d shashwatwork/dataco-smart-supply-chain-for-big-data-analysis
unzip dataco-smart-supply-chain-for-big-data-analysis.zip -d data/
```

