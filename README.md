# Gail Breast Cancer Risk — Research and Demonstration Toolkit

This repository contains a **browser-only NCI BCRAT input checklist**, a Python collection of clinical calculation helpers, and a **separate demonstration-only** FastAPI rules engine with an in-memory HMAC audit log.

**Clinical limitation:** No calibrated Gail/BCRAT absolute-risk calculation is implemented here. The generic score and operational alert thresholds are arbitrary examples, **not** estimates of 5-year or lifetime breast-cancer risk. Use the [NCI Breast Cancer Risk Assessment Tool](https://bcrisktool.cancer.gov/) for validated estimates, subject to its eligibility and limitations.

## Browser checklist

Open `docs/index.html` directly in a browser to prepare non-identifying risk-factor answers, review them, and open the official NCI calculator. The checklist does not estimate risk; answers are not transmitted, saved to browser storage, or transferred automatically to the NCI website. Do not enter patient identifiers.

GitHub Pages deployment is defined in `.github/workflows/pages.yml`; availability depends on Pages being enabled for this repository. Until independently verified, use the local file or the NCI calculator directly.

## Python functions

`gail.py` exposes:

- `calculate_meld_na`: legacy MELD-Na equation (not MELD 3.0).
- `calculate_qtc`: Bazett QT correction.
- `calculate_bmi_z`: BMI with an **unvalidated simplified** z-score approximation; not a WHO/CDC percentile or z-score.
- `convert_hba1c`: HbA1c ↔ eAG via the ADAG linear relationship.
- `calculate_apri_fib4`: APRI and FIB-4 with simplified input defaults.
- `calculate_score`: legacy numeric **demonstration score only**, not a medical risk model.

All calculations require input review and independent validation before any clinical use. The `assess_row` dispatcher explicitly rejects Gail-specific questionnaire fields rather than creating a fictitious risk estimate.

### Install, test, and use

Requires Python 3.10 or later.

```bash
python -m pip install -e ".[test]"
python -m compileall -q .
pytest -q
python gail.py single --json '{"qt_ms":400,"hr_bpm":60}'
python gail.py batch --input sample.csv --output results.csv
```

The `gail` entry point invokes the numerical dispatcher. The separate `gail-cli` entry point starts the demonstration supervisor and provides `audit`, `batch`, `chat`, `verify-audit`, and `serve` subcommands.

## Local FastAPI demonstration

The API applies generic configurable-in-code thresholds to non-identifying task codes. It is not a breast-cancer risk-assessment endpoint. Only `/health`, `/metrics`, and `/` are public; `/api/audit`, `/api/chat`, and `/api/audit/logs` require the `X-API-Key` header matching `GAIL_API_KEY`. Without this setting, operational endpoints are unavailable.

```bash
export AUDIT_SECRET_KEY="$(python -c 'import secrets; print(secrets.token_hex(32))')"
export GAIL_API_KEY="$(python -c 'import secrets; print(secrets.token_urlsafe(32))')"
python cli.py serve --host 127.0.0.1 --port 8000
```

Open [http://127.0.0.1:8000/](http://127.0.0.1:8000/) and supply the local API key in the interface. The key is used only for the current request and is not persisted by the browser. The API schema is available locally at `/docs` and `/openapi.json`.

### Docker Compose

Set `AUDIT_SECRET_KEY` and `GAIL_API_KEY` in the shell, then run:

```bash
docker compose up --build
```

Compose binds to `127.0.0.1:8000`, not a public network interface. Use appropriate TLS, network access control, and authentication if deploying behind a reverse proxy.

## Security and data handling

The service checks some common identifier patterns before tasks are processed, but **regex filtering does not guarantee de-identification or HIPAA compliance**. Do not submit PHI. Audit records are held **in memory**, and disappear when the process restarts. HMAC signatures verify that stored records have not been altered within the running process, but do not provide durable, independently anchored audit evidence. A temporary random key is generated when `AUDIT_SECRET_KEY` is omitted, making signatures nonpersistent across restarts.

Do not commit credentials, patient data, or production audit keys. A development key previously appeared in the repository's history: **rotate it immediately if it was ever used**.

## Architecture and compatibility

- Python 3.10+, FastAPI, Pydantic v2, Uvicorn and pytest.
- Standalone static browser checklist: HTML/CSS/JavaScript with no Python runtime and no network dependency for the checklist itself.
- Local API console: HTML/JavaScript calling the same-origin FastAPI backend.
- The back-end calculations require Python; GitHub Pages hosts **only the checklist**, not the FastAPI service or the Python calculation library.
- CI runs installation, compilation, tests and browser-script syntax checks on Python 3.10, 3.11 and 3.12.

## License

[MIT](LICENSE).

## Reference

[National Cancer Institute — Breast Cancer Risk Assessment Tool (Gail Model)](https://bcrisktool.cancer.gov/about.html). The official NCI model uses age, reproductive history, family history, prior biopsies, atypical hyperplasia and race/ethnicity with population-calibrated risk estimates.
