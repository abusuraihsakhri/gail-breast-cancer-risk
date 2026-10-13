"""Regression checks for audit integrity, API authentication, and clinical labeling."""
import math
import re
import shutil
import subprocess
from pathlib import Path

import pytest
from fastapi import HTTPException

from agents.api import require_api_key
from agents.base import AuditTrail
from gail import _safe_float, assess_row, calculate_score, process_csv


def test_hmac_chain_verifies_signatures_not_only_links():
    trail = AuditTrail("unit-test-secret")
    trail.log("tester", "operator", "test_event", {"status": "ok"})
    trail.log("tester", "operator", "other_event", {"status": "ok"})
    assert trail.verify_integrity()
    trail.logs[0]["actor"] = "tampered"
    assert not trail.verify_integrity()


def test_hmac_chain_rejects_modified_tail_signature():
    trail = AuditTrail("unit-test-secret")
    trail.log("tester", "operator", "test_event", {"status": "ok"})
    trail.logs[-1]["current_hash"] = "f" * 64
    assert not trail.verify_integrity()


def test_audit_trail_snapshot_is_not_mutable_internal_state():
    trail = AuditTrail("unit-test-secret")
    trail.log("tester", "operator", "test_event", {"status": "ok"})
    snapshot = trail.get_trail()
    snapshot[0]["actor"] = "tampered"
    assert trail.verify_integrity()
    assert trail.get_trail()[0]["actor"] == "tester"


def test_default_development_keys_are_not_shared(monkeypatch):
    monkeypatch.delenv("AUDIT_SECRET_KEY", raising=False)
    with pytest.warns(UserWarning):
        one = AuditTrail()
    with pytest.warns(UserWarning):
        two = AuditTrail()
    assert one.secret_key != two.secret_key


def test_operational_api_requires_configured_token(monkeypatch):
    monkeypatch.delenv("GAIL_API_KEY", raising=False)
    with pytest.raises(HTTPException) as exc:
        require_api_key("any-token")
    assert exc.value.status_code == 503
    monkeypatch.setenv("GAIL_API_KEY", "test-token")
    with pytest.raises(HTTPException) as exc:
        require_api_key("wrong-token")
    assert exc.value.status_code == 401
    assert require_api_key("test-token") is None


def test_risk_questionnaire_is_not_misrepresented():
    result = assess_row({
        "age": 47, "age_at_menarche": "12-13",
        "first_degree_relatives": 1, "breast_biopsies": 0
    })
    assert "error" in result
    assert "bcrisktool.cancer.gov" in result["reference"]
    assert "score" not in result
    assert "not validated" in calculate_score(value=10)["clinical_validity"]


@pytest.mark.parametrize("input_value", ["nan", "inf", "-inf", math.nan, math.inf])
def test_non_finite_numeric_inputs_are_rejected(input_value):
    assert _safe_float(input_value, default=5.0) == 5.0


def test_csv_outputs_have_stable_column_order(tmp_path):
    source = tmp_path / "rows.csv"
    output = tmp_path / "out.csv"
    source.write_text("qt_ms,rr_ms\n400,1000\n", encoding="utf-8")
    process_csv(source, output)
    columns = output.read_text(encoding="utf-8").splitlines()[0].split(",")
    assert columns[:2] == ["qt_ms", "rr_ms"]
    assert columns[2:] == sorted(columns[2:])


@pytest.mark.parametrize("relative", ["docs/index.html", "web/index.html"])
def test_browser_script_has_valid_syntax(relative, tmp_path):
    if not shutil.which("node"):
        pytest.skip("node is not available")
    page = (Path(__file__).resolve().parents[1] / relative).read_text(encoding="utf-8")
    matches = re.findall(r"<script(?:\s[^>]*)?>(.*?)</script>", page, flags=re.DOTALL)
    assert len(matches) == 1
    script = tmp_path / "script.js"
    script.write_text(matches[0], encoding="utf-8")
    subprocess.run(["node", "--check", str(script)], check=True, capture_output=True, text=True)


def test_static_checklist_does_not_fabricate_risk():
    html = (Path(__file__).resolve().parents[1] / "docs/index.html").read_text(encoding="utf-8")
    assert "does not calculate breast-cancer risk" in html
    assert "https://bcrisktool.cancer.gov/" in html
    assert "localStorage" not in html
