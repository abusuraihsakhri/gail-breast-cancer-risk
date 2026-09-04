"""
Automated Pytest for gail.py clinical calculation functions.
"""
import sys
import math
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from gail import (
    calculate_score,
    calculate_meld_na,
    calculate_qtc,
    calculate_bmi_z,
    convert_hba1c,
    calculate_apri_fib4,
    assess_row,
    _safe_float,
)


class TestSafeFloat:
    def test_none_returns_default(self):
        assert _safe_float(None) == 0.0

    def test_valid_number(self):
        assert _safe_float(3.14) == 3.14

    def test_string_number(self):
        assert _safe_float("42.5") == 42.5

    def test_invalid_string(self):
        assert _safe_float("abc", default=1.0) == 1.0

    def test_custom_default(self):
        assert _safe_float(None, default=5.0) == 5.0


class TestCalculateScore:
    def test_basic_score(self):
        result = calculate_score(value=10, weight=20)
        assert "score" in result
        assert "inputs" in result
        assert result["inputs"] == 2

    def test_empty_kwargs(self):
        result = calculate_score()
        assert "score" in result
        assert result["inputs"] == 1

    def test_string_numeric_values(self):
        result = calculate_score(a="5", b="10.5")
        assert result["score"] > 0


class TestCalculateMeldNa:
    def test_basic_meld_na(self):
        result = calculate_meld_na(bilirubin=2.0, creatinine=1.5, inr=1.2, sodium=135)
        assert result["score_type"] == "MELD-Na"
        assert "meld_na" in result
        assert 6.0 <= result["meld_na"] <= 40.0

    def test_dialysis_caps_creatinine(self):
        result = calculate_meld_na(bilirubin=1.0, creatinine=0.5, inr=1.0, sodium=137, dialysis=True)
        assert result["creatinine"] == 4.0

    def test_flooring(self):
        result = calculate_meld_na(bilirubin=0.1, creatinine=0.1, inr=0.1)
        assert result["bilirubin"] >= 1.0
        assert result["creatinine"] >= 1.0
        assert result["inr"] >= 1.0

    def test_none_values_use_defaults(self):
        result = calculate_meld_na(bilirubin=None, creatinine=None)
        assert result["score_type"] == "MELD-Na"

    def test_string_inputs(self):
        result = calculate_meld_na(bilirubin="2.5", creatinine="1.8", inr="1.3")
        assert result["score_type"] == "MELD-Na"
        assert result["meld_na"] > 0


class TestCalculateQtc:
    def test_basic_qtc_from_hr(self):
        result = calculate_qtc(qt_ms=400, hr_bpm=60)
        assert result["score_type"] == "QTc"
        assert "qtc_ms" in result
        assert result["qtc_ms"] > 0

    def test_qtc_from_rr(self):
        result = calculate_qtc(qt_ms=400, rr_ms=1000)
        assert result["score_type"] == "QTc"
        assert result["rr_s"] == 1.0

    def test_prolonged_qtc(self):
        result = calculate_qtc(qt_ms=500, hr_bpm=60)
        assert result["prolonged"] is True

    def test_normal_qtc(self):
        result = calculate_qtc(qt_ms=380, hr_bpm=70)
        assert result["prolonged"] is False

    def test_none_rr_uses_hr(self):
        result = calculate_qtc(qt_ms=400, rr_ms=None, hr_bpm=60)
        assert result["score_type"] == "QTc"


class TestCalculateBmiZ:
    def test_basic_bmi(self):
        result = calculate_bmi_z(weight_kg=70, height_cm=175, age_months=360)
        assert result["score_type"] == "BMI-z"
        expected_bmi = 70 / (1.75 ** 2)
        assert abs(result["bmi"] - expected_bmi) < 0.01

    def test_z_score_present(self):
        result = calculate_bmi_z(weight_kg=70, height_cm=175, age_months=360)
        assert "z_score" in result

    def test_zero_height_safe(self):
        result = calculate_bmi_z(weight_kg=70, height_cm=0, age_months=60)
        assert result["bmi"] > 0  # Should not crash


class TestConvertHba1c:
    def test_hba1c_to_eag(self):
        result = convert_hba1c(hba1c_percent=6.0)
        assert result["score_type"] == "HbA1c-eAG"
        expected_eag = 28.7 * 6.0 - 46.7
        assert abs(result["eag_mgdl"] - expected_eag) < 0.1

    def test_eag_to_hba1c(self):
        result = convert_hba1c(eag_mgdl=154.0)
        assert result["estimated_from"] == "eag"
        assert result["hba1c_percent"] > 0

    def test_no_inputs(self):
        result = convert_hba1c()
        assert "error" in result


class TestCalculateAprFib4:
    def test_basic_calculation(self):
        result = calculate_apri_fib4(ast_u_l=40, alt_u_l=30, platelets_109=200, age_years=45)
        assert result["score_type"] == "APRI-FIB4"
        assert "apri" in result
        assert "fib4" in result
        assert result["apri"] >= 0
        assert result["fib4"] >= 0

    def test_none_values_safe(self):
        result = calculate_apri_fib4(ast_u_l=30)
        assert result["score_type"] == "APRI-FIB4"


class TestAssessRow:
    def test_meld_na_route(self):
        result = assess_row({"bilirubin": 2.0, "creatinine": 1.5})
        assert result["score_type"] == "MELD-Na"

    def test_qtc_route_with_qt_ms(self):
        result = assess_row({"qt_ms": 400, "hr_bpm": 70})
        assert result["score_type"] == "QTc"

    def test_qtc_route_with_qt_alias(self):
        result = assess_row({"qt": 400, "rr_ms": 800})
        assert result["score_type"] == "QTc"

    def test_bmi_route(self):
        result = assess_row({"weight_kg": 70, "height_cm": 165})
        assert result["score_type"] == "BMI-z"

    def test_hba1c_route(self):
        result = assess_row({"hba1c_percent": 6.5})
        assert result["score_type"] == "HbA1c-eAG"

    def test_apri_fib4_route(self):
        result = assess_row({"ast_u_l": 40, "alt_u_l": 30, "platelets_109": 200})
        assert result["score_type"] == "APRI-FIB4"

    def test_fallback_to_score(self):
        result = assess_row({"value": 10})
        assert "score" in result

    def test_error_handling(self):
        # Should not crash, returns dict with error
        result = assess_row({"bilirubin": "invalid", "creatinine": "invalid"})
        assert isinstance(result, dict)
