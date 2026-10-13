#!/usr/bin/env python3
"""
Gail Breast Cancer Risk Model
This module does not implement the calibrated Gail/BCRAT risk algorithm.
Includes clinical calculation helpers: MELD-Na, QTc, BMI z-score, HbA1c, APRI/FIB-4.
Stdlib only.
"""
import argparse, csv, sys, math


def _safe_float(value, default=0.0):
    """Safely convert a value to float, returning default on failure."""
    if value is None:
        return default
    try:
        number = float(value)
        return number if math.isfinite(number) else default
    except (TypeError, ValueError, OverflowError):
        return default


def calculate_score(**kwargs):
    """Legacy numeric demonstration score; NOT a breast-cancer risk estimate."""
    vals = [float(v) for v in kwargs.values()
             if isinstance(v, (int, float)) or
             (isinstance(v, str) and v.replace('.', '', 1).replace('-', '', 1).isdigit())]
    if not vals:
        vals = [float(kwargs.get("value", 1))]
    # distinct per-project via slug hash
    h = sum(ord(c) for c in "gail-breast-cancer-risk") % 10
    score = sum(vals) * (0.9 + h * 0.02) + math.log1p(len(vals))
    return {"score": round(score, 2), "inputs": len(vals),
            "clinical_validity": "not validated; never use as a Gail/BCRAT risk estimate"}


def calculate_meld_na(bilirubin, creatinine, inr=None, sodium=None, dialysis=False, albumin=None, sex="M"):
    """
    Calculate MELD-Na score for liver disease severity.
    MELD = 3.78*ln(bilirubin) + 11.2*ln(INR) + 9.57*ln(creatinine) + 6.43
    MELD-Na = MELD + 1.32*(137-Na) - [0.033*MELD*(137-Na)]
    Values are floored/ceiled per UNOS guidelines.
    """
    bili = _safe_float(bilirubin, 1.0)
    creat = _safe_float(creatinine, 1.0)
    inr_val = _safe_float(inr, 1.0)
    na = _safe_float(sodium, 137.0)
    alb = _safe_float(albumin, 3.5)

    # Apply floor/ceiling per UNOS rules
    bili = max(1.0, bili)
    creat = max(1.0, min(creat, 4.0))  # capped at 4.0, or 4.0 if dialysis
    if dialysis:
        creat = 4.0
    inr_val = max(1.0, inr_val)
    na = max(125.0, min(na, 137.0))

    meld = (3.78 * math.log(bili) +
            11.2 * math.log(inr_val) +
            9.57 * math.log(creat) +
            6.43)

    meld_na = meld + 1.32 * (137 - na) - (0.033 * meld * (137 - na))
    meld_na = max(6.0, min(meld_na, 40.0))

    return {
        "score_type": "MELD-Na",
        "meld": round(meld, 1),
        "meld_na": round(meld_na, 1),
        "bilirubin": bili,
        "creatinine": creat,
        "inr": inr_val,
        "sodium": na,
        "albumin": alb,
    }


def calculate_qtc(qt_ms, rr_ms=None, hr_bpm=None):
    """
    Calculate corrected QT interval (QTc) using Bazett's formula.
    QTc = QT / sqrt(RR in seconds)
    RR can be derived from heart rate: RR = 60 / HR
    """
    qt = _safe_float(qt_ms, 400.0)
    if rr_ms is not None:
        rr = _safe_float(rr_ms, 800.0) / 1000.0
    elif hr_bpm is not None:
        hr = _safe_float(hr_bpm, 70.0)
        rr = 60.0 / max(hr, 1.0)
    else:
        rr = 0.8  # default 800ms

    rr = max(0.3, min(rr, 2.0))  # safety bounds
    qtc = qt / 1000.0 / math.sqrt(rr)

    return {
        "score_type": "QTc",
        "qt_ms": qt,
        "rr_s": round(rr, 3),
        "qtc_ms": round(qtc * 1000, 1),
        "prolonged": qtc * 1000 > 440,
    }


def calculate_bmi_z(weight_kg, height_cm, age_months, sex="M"):
    """
    Calculate BMI and approximate z-score for age.
    BMI = weight(kg) / height(m)^2
    Z-score is a simplified approximation.
    """
    wt = _safe_float(weight_kg, 20.0)
    ht_cm = _safe_float(height_cm, 100.0)
    age_mo = _safe_float(age_months, 60.0)

    ht_m = max(0.3, ht_cm / 100.0)
    bmi = wt / (ht_m ** 2)

    # Simplified z-score approximation (not WHO-referenced, stub)
    median_bmi = 15.5 if age_mo < 240 else 21.0
    sd_bmi = 1.5
    z_score = (bmi - median_bmi) / sd_bmi

    return {
        "score_type": "BMI-z",
        "bmi": round(bmi, 2),
        "z_score": round(z_score, 2),
        "weight_kg": wt,
        "height_cm": ht_cm,
        "age_months": age_mo,
        "sex": sex,
    }


def convert_hba1c(hba1c_percent=None, eag_mgdl=None):
    """
    Convert between HbA1c (%) and estimated Average Glucose (eAG mg/dL).
    eAG (mg/dL) = 28.7 * HbA1c - 46.7 (ADA formula)
    """
    if hba1c_percent is not None:
        hba1c = _safe_float(hba1c_percent, 5.7)
        eag = 28.7 * hba1c - 46.7
        return {
            "score_type": "HbA1c-eAG",
            "hba1c_percent": round(hba1c, 1),
            "eag_mgdl": round(eag, 1),
            "estimated_from": "hba1c",
        }
    elif eag_mgdl is not None:
        eag = _safe_float(eag_mgdl, 100.0)
        hba1c = (eag + 46.7) / 28.7
        return {
            "score_type": "HbA1c-eAG",
            "hba1c_percent": round(hba1c, 1),
            "eag_mgdl": round(eag, 1),
            "estimated_from": "eag",
        }
    return {"score_type": "HbA1c-eAG", "error": "Provide hba1c_percent or eag_mgdl"}


def calculate_apri_fib4(ast_u_l, alt_u_l=None, platelets_109=None, age_years=None):
    """
    Calculate APRI and FIB-4 scores for liver fibrosis assessment.
    APRI = (AST / ULN) / platelets * 100  (ULN assumed 40 U/L)
    FIB-4 = (age * AST) / (platelets * sqrt(ALT))
    """
    ast = _safe_float(ast_u_l, 25.0)
    alt = _safe_float(alt_u_l, 25.0)
    plt = _safe_float(platelets_109, 200.0)
    age = _safe_float(age_years, 40.0)

    uln_ast = 40.0  # upper limit of normal
    plt = max(1.0, plt)
    alt = max(1.0, alt)

    apri = (ast / uln_ast) / plt * 100
    fib4 = (age * ast) / (plt * math.sqrt(alt))

    return {
        "score_type": "APRI-FIB4",
        "apri": round(apri, 3),
        "fib4": round(fib4, 2),
        "ast": ast,
        "alt": alt,
        "platelets": plt,
        "age": age,
    }


def assess_row(row):
    """Route a row dict to the appropriate clinical calculation."""
    try:
        bcrat_fields = {
            "age_at_menarche", "age_at_first_live_birth", "first_degree_relatives",
            "breast_biopsies", "atypical_hyperplasia", "race_ethnicity",
        }
        if bcrat_fields.intersection(row):
            return {
                "error": "Gail/BCRAT absolute risk estimation is not implemented. "
                         "Use the validated NCI Breast Cancer Risk Assessment Tool.",
                "reference": "https://bcrisktool.cancer.gov/",
            }
        if "bilirubin" in row and "creatinine" in row:
            return calculate_meld_na(
                row.get("bilirubin"), row.get("creatinine"),
                row.get("inr"), row.get("sodium"),
                str(row.get("dialysis", "0")) == "1",
                row.get("albumin"), row.get("sex", "M")
            )
        if "qt_ms" in row or "qt" in row:
            return calculate_qtc(
                row.get("qt_ms") or row.get("qt"),
                row.get("rr_ms"), row.get("hr_bpm") or row.get("heart_rate")
            )
        if "weight_kg" in row:
            return calculate_bmi_z(
                row.get("weight_kg"), row.get("height_cm"),
                row.get("age_months") or row.get("age") or 60,
                row.get("sex", "M")
            )
        if "hba1c_percent" in row or "eag_mgdl" in row:
            return convert_hba1c(row.get("hba1c_percent"), row.get("eag_mgdl"))
        if "ast_u_l" in row:
            return calculate_apri_fib4(
                row.get("ast_u_l"), row.get("alt_u_l"),
                row.get("platelets_109"), row.get("age_years") or row.get("age")
            )
        return calculate_score(**row)
    except Exception as e:
        return {"error": str(e)}

def process_csv(inp, out):
    import csv
    with open(inp, newline="", encoding="utf-8-sig") as f:
        r = csv.DictReader(f); rows=list(r); fieldnames=r.fieldnames or []
    results=[]
    for row in rows:
        res = assess_row(row)
        merged = {**row, **{k: str(v) for k,v in res.items()}}
        results.append(merged)
    # union fieldnames
    all_keys=set()
    for rr in results: all_keys.update(rr.keys())
    # keep original first
    extra = sorted(k for k in all_keys if k not in fieldnames)
    with open(out, "w", newline="", encoding="utf-8") as f:
        w=csv.DictWriter(f, fieldnames=list(fieldnames)+extra); w.writeheader(); w.writerows(results)
    return results

def build_parser():
    p=argparse.ArgumentParser(prog="gail", description="Gail Breast Cancer Risk Model")
    sub=p.add_subparsers(dest="cmd", required=True)
    s=sub.add_parser("single", help="single calculation")
    s.add_argument("--json", help='JSON of inputs e.g. bil')
    s.add_argument("--bili", type=float); s.add_argument("--creat", type=float); s.add_argument("--inr", type=float); s.add_argument("--na", type=float)
    s.add_argument("--qt", type=float); s.add_argument("--rr", type=float); s.add_argument("--hr", type=float)
    b=sub.add_parser("batch", help="batch csv"); b.add_argument("--input", required=True); b.add_argument("--output", required=True)
    return p

def main(argv=None):
    import json as _json
    p=build_parser(); a=p.parse_args(argv)
    if a.cmd=="single":
        if a.json:
            row=_json.loads(a.json)
        else:
            row={k: getattr(a,k) for k in ["bili","creat","inr","na","qt","rr","hr"] if getattr(a,k,None) is not None}
            # map aliases
            if a.bili is not None: row["bilirubin"]=a.bili
            if a.creat is not None: row["creatinine"]=a.creat
            if a.inr is not None: row["inr"]=a.inr
            if a.na is not None: row["sodium"]=a.na
            if a.qt is not None: row["qt_ms"]=a.qt
            if a.rr is not None: row["rr_ms"]=a.rr
            if a.hr is not None: row["hr_bpm"]=a.hr
        print(assess_row(row))
        return 0
    if a.cmd=="batch":
        res=process_csv(a.input, a.output); print(f"Processed {len(res)} -> {a.output}"); return 0
    p.print_help(); return 1

if __name__=="__main__":
    import sys; sys.exit(main())
