# Gail Breast Cancer Risk

> **Domain:** Medical Oncology & Clinical Decision Support  
> **Standards Reference:** AJCC Cancer Staging Manual, NCCN Clinical Practice Guidelines

<div align="center">

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
![Python](https://img.shields.io/badge/Python-3.10%20%7C%203.11%20%7C%203.12-3776AB.svg?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688.svg?logo=fastapi&logoColor=white)
![Audit Trail](https://img.shields.io/badge/Audit-HMAC--SHA256_Tamper--Evident-brightgreen.svg)
![Zero-PHI Guard](https://img.shields.io/badge/Guard-Zero--PHI_Outbound-blue.svg)
![Docker](https://img.shields.io/badge/Docker-Ready-2496ED.svg?logo=docker&logoColor=white)

</div>

---

## Overview

Gail Breast Cancer Risk is a clinical decision support toolkit providing:

- **Gail 5-year and lifetime risk approximation** from questionnaire inputs with SEER calibration stub
- **Clinical calculation helpers**: MELD-Na, QTc (Bazett), BMI z-score, HbA1c/eAG conversion, APRI/FIB-4
- **Enterprise audit trail**: HMAC-SHA256 tamper-evident chained logging
- **Zero-PHI outbound guard**: AST and regex inspection blocking SSNs, MRNs, phone numbers, emails, and patient identifiers
- **FastAPI REST server**: OpenAPI 3.1 endpoints for task evaluation and supervisory chat
- **Distributed agent workers**: Multi-worker evaluation pipeline with consensus dossier generation

---

## Installation

```bash
# Clone the repository
git clone https://github.com/abusuraihsakhri/gail-breast-cancer-risk.git
cd gail-breast-cancer-risk

# Install with dependencies
pip install -e ".[test]"
```

Or install runtime dependencies only:

```bash
pip install fastapi uvicorn pydantic
```

---

## Usage

### CLI Tool

```bash
# Run single task evaluation
python cli.py audit --task-id TASK-001 --target KEY-01 --primary 28.5 --secondary 14.2

# Supervisory chat query
python cli.py chat "Explain risk stratification protocol"

# Batch process CSV records
python cli.py batch -i input.csv -o results.csv

# Verify HMAC audit trail integrity
python cli.py verify-audit

# Launch FastAPI REST server
python cli.py serve --host 127.0.0.1 --port 8000
```

### Direct Calculation API

```python
from gail import calculate_meld_na, calculate_qtc, calculate_bmi_z, convert_hba1c, calculate_apri_fib4

# MELD-Na score
result = calculate_meld_na(bilirubin=2.5, creatinine=1.8, inr=1.3, sodium=132)
print(result)  # {'score_type': 'MELD-Na', 'meld_na': ..., ...}

# QTc calculation
result = calculate_qtc(qt_ms=420, hr_bpm=72)
print(result)  # {'score_type': 'QTc', 'qtc_ms': ..., ...}

# BMI z-score
result = calculate_bmi_z(weight_kg=70, height_cm=165, age_months=360)
print(result)  # {'score_type': 'BMI-z', 'bmi': ..., ...}

# HbA1c to eAG conversion
result = convert_hba1c(hba1c_percent=6.5)
print(result)  # {'score_type': 'HbA1c-eAG', 'eag_mgdl': ..., ...}

# APRI and FIB-4 scores
result = calculate_apri_fib4(ast_u_l=45, alt_u_l=35, platelets_109=180, age_years=50)
print(result)  # {'score_type': 'APRI-FIB4', 'apri': ..., 'fib4': ...}
```

### REST API

```bash
# Start server
python cli.py serve

# Health check
curl http://localhost:8000/health

# Submit audit task
curl -X POST http://localhost:8000/api/audit \
  -H "Content-Type: application/json" \
  -d '{"task_id":"T1","target_identifier":"KEY-01","primary_metric":25.0}'

# Prometheus metrics
curl http://localhost:8000/metrics

# Audit trail
curl http://localhost:8000/api/audit/logs
```

---

## Clinical Calculation Reference

| Function | Description | Formula |
|:---------|:------------|:--------|
| `calculate_meld_na()` | Liver disease severity (MELD-Na) | UNOS MELD-Na with floor/ceiling bounds |
| `calculate_qtc()` | Corrected QT interval | Bazett: QT / sqrt(RR) |
| `calculate_bmi_z()` | BMI with z-score approximation | BMI = kg / m^2 |
| `convert_hba1c()` | HbA1c ↔ eAG conversion | ADA: eAG = 28.7 * HbA1c - 46.7 |
| `calculate_apri_fib4()` | Liver fibrosis scores | APRI, FIB-4 per standard definitions |

---

## Security Features

- **Zero-PHI Outbound Guard:** Blocks SSNs, MRNs, phone numbers, emails, DOB patterns, and common patient name patterns
- **HMAC-SHA256 Audit Trail:** Chained, cryptographically signed log entries
- **PHI Redaction:** Automatic redaction of detected identifiers in outbound content
- **Environment-based secret key:** `AUDIT_SECRET_KEY` environment variable required for production

---

## Testing

```bash
# Run full test suite
pytest -v

# Run specific test file
pytest tests/test_gail_breast_cancer_risk.py -v
pytest tests/test_enrichment.py -v
```

Run the stress test simulator:

```bash
python simulator.py 1000
```

---

## Docker Deployment

```bash
docker build -t gail-breast-cancer-risk .
docker run -p 8000:8000 -e AUDIT_SECRET_KEY=<your-secret-key> gail-breast-cancer-risk
```

Or with docker-compose:

```bash
docker-compose up -d
```

---

## Project Structure

```
gail-breast-cancer-risk/
├── agents/                 # Enterprise agent suite
│   ├── __init__.py
│   ├── api.py              # FastAPI REST endpoints
│   ├── base.py             # Security, PHI guard, HMAC audit trail
│   ├── learning.py         # Bayesian calibration engine
│   ├── llm_factory.py      # LLM provider factory
│   ├── metrics.py          # Prometheus metrics collector
│   ├── models.py           # Pydantic data models
│   ├── streamer.py         # WebSocket telemetry
│   ├── supervisor.py       # Multi-agent orchestrator
│   └── workers.py          # Specialized evaluation workers
├── tests/                  # Test suite
│   ├── test_enrichment.py
│   └── test_gail_breast_cancer_risk.py
├── cli.py                  # Command-line interface
├── enrichment.py           # Feature enrichment engines
├── gail.py                 # Clinical calculation library
├── simulator.py            # High-throughput stress testing
├── web/index.html          # Operations console UI
├── pyproject.toml          # Python packaging config
├── Dockerfile              # Container build
└── docker-compose.yml      # Container orchestration
```
