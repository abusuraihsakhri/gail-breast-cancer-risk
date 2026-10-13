"""
FastAPI REST API Server for Gail Breast Cancer Risk.
"""
import hmac
import os
from pathlib import Path
from typing import Dict, Any, List
from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.responses import FileResponse
from pydantic import BaseModel
from .base import AuditLogger, PHIGuard
from .models import SystemTaskPayload, ConsensusDossier
from .supervisor import SystemSupervisor

supervisor = SystemSupervisor(model_provider="mock")

app = FastAPI(
    title="Gail Breast Cancer Risk API",
    description="Enterprise Distributed Component Platform (Clinical & Biomedical AI)",
    version="3.0.0-ENTERPRISE",
)


def require_api_key(x_api_key: str | None = Header(default=None)) -> None:
    """Fail closed on operational endpoints without a configured secret."""
    configured = os.getenv("GAIL_API_KEY")
    if not configured:
        raise HTTPException(status_code=503, detail="Set GAIL_API_KEY to enable API endpoints")
    if x_api_key is None or not hmac.compare_digest(x_api_key, configured):
        raise HTTPException(status_code=401, detail="Invalid API key")


@app.get("/", include_in_schema=False)
def index():
    return FileResponse(Path(__file__).resolve().parent.parent / "web" / "index.html")


class ChatRequest(BaseModel):
    query: str


@app.get("/health")
def health():
    return {"status": "HEALTHY", "service": "gail-breast-cancer-risk", "domain": "Clinical & Biomedical AI", "standard": "CAP / CLSI / ISO Standards", "version": "3.0.0-ENTERPRISE"}


@app.get("/metrics")
def metrics():
    return {
        "dossiers_processed_total": len(supervisor.dossier_registry),
        "audit_blocks_total": len(AuditLogger.get_trail()),
        "system_status": "NOMINAL_OPTIMAL"
    }


@app.post("/api/audit", dependencies=[Depends(require_api_key)])
def api_audit(payload: SystemTaskPayload):
    dossier = supervisor.process_task(payload)
    return dossier.to_dict()


@app.post("/api/chat", dependencies=[Depends(require_api_key)])
def api_chat(req: ChatRequest):
    try:
        ans = supervisor.query_supervisory_chat(req.query)
        return {"response": ans}
    except Exception as e:
        raise HTTPException(status_code=400, detail="Request rejected") from e


@app.get("/api/audit/logs", dependencies=[Depends(require_api_key)])
def api_audit_logs():
    return {"audit_trail": AuditLogger.get_trail(), "verified": AuditLogger.verify_integrity()}
