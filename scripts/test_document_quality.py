#!/usr/bin/env animamus_env/bin/python
"""
문서 생성 품질 테스트 — 전체 환자 × 5가지 문서 유형 일괄 검증

사용법 (sagepontus/ 디렉터리에서):
    animamus_env/bin/python scripts/test_document_quality.py
    animamus_env/bin/python scripts/test_document_quality.py --username chrisnam
    animamus_env/bin/python scripts/test_document_quality.py --verbose
    animamus_env/bin/python scripts/test_document_quality.py --patient PT-014

검사 항목:
    - onset       : "As documented in initial evaluation" fallback 텍스트 감지
    - goals       : "Refer to session SOAP documentation" / hardcoded 기본 목표
    - obj         : "(See session SOAP documentation)" — MMT/ROM/special tests 없음
    - func        : "Activity limitations requiring skilled therapeutic intervention"

반환 기준:
    - ✓  : 모든 fallback 텍스트 없음 (실제 임상 데이터 사용)
    - ✗  : 하나 이상의 fallback 텍스트 포함 (원인 태그 표시)
    - ERR: 문서 생성 예외 발생
"""

import django
import os
import sys

# sagepontus/ 루트를 sys.path에 추가 (scripts/ 하위에서 실행 시)
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "animamus_project.settings")
django.setup()

import argparse
from django.contrib.auth.models import User
from vertical_pt.models import PatientTimeline
from vertical_pt.engine import build_patient_context
from vertical_pt.engine.documents import generate_document, DOC_TITLES
from vertical_pt.views.views_pt_alarm import _soap_goals_fallback

# ── fallback 탐지 패턴 ────────────────────────────────────────────
FALLBACK_CHECKS = {
    "onset": [
        "As documented in initial evaluation",
    ],
    "goals": [
        "Refer to session SOAP documentation",
        "Short-Term:  Reduce risk score below 0.25",
        "Long-Term:   Return to prior level of function",
    ],
    "obj": [
        "(See session SOAP documentation)",
    ],
    "func": [
        "Activity limitations requiring skilled therapeutic intervention",
    ],
}

_INTERNAL_KEYS = {"soap_section_overrides"}
DOC_TYPES = list(DOC_TITLES.keys())
DOC_SHORT = {
    "medical_necessity":   "MedNec ",
    "legal_defense":       "Legal  ",
    "clinical_chronology": "Chron  ",
    "insurance_appeal":    "Appeal ",
    "functional_report":   "FuncRp ",
}


def get_clinical_context(sessions):
    ctx = {}
    for s in reversed(sessions):
        c = {k: v for k, v in (s.clinical_context or {}).items() if k not in _INTERNAL_KEYS}
        if any(v for v in c.values() if v):
            ctx = c
            break
    fb = _soap_goals_fallback(sessions)
    for key in ("goals_ltg", "goals_stg", "onset_duration", "functional_limitations"):
        if not ctx.get(key) and fb.get(key):
            ctx[key] = fb[key]
    return ctx


def check_doc(doc_text):
    """fallback 텍스트 탐지 → {태그: 발견된 구문} 반환."""
    issues = {}
    for tag, phrases in FALLBACK_CHECKS.items():
        for ph in phrases:
            if ph in doc_text:
                issues[tag] = ph
                break
    return issues


def run_test(username="chrisnam", target_pid=None, verbose=False):
    try:
        user = User.objects.get(username=username)
    except User.DoesNotExist:
        print(f"User '{username}' not found.")
        sys.exit(1)

    pids = sorted(
        PatientTimeline.objects.filter(therapist=user)
        .values_list("patient_id", flat=True)
        .distinct()
    )
    if target_pid:
        pids = [p for p in pids if p == target_pid]
        if not pids:
            print(f"Patient '{target_pid}' not found for user '{username}'.")
            sys.exit(1)

    results = {}
    all_issues = {}
    ok_count = 0
    total = 0

    for pid in pids:
        sessions = list(
            PatientTimeline.objects.filter(therapist=user, patient_id=pid)
            .prefetch_related("alerts")
            .order_by("session_date", "created_at")
        )
        ctx = get_clinical_context(sessions)
        patient_ctx = build_patient_context(pid, user.id)
        therapist = user.get_full_name() or user.username
        results[pid] = {
            "name": sessions[0].patient_name,
            "n": len(sessions),
            "docs": {},
            "ctx_summary": {
                "onset":   bool(ctx.get("onset_duration")),
                "goals":   bool(ctx.get("goals_ltg") or ctx.get("goals_stg")),
                "obj":     bool(ctx.get("mmt_findings") or ctx.get("rom_findings")),
                "func":    bool(ctx.get("functional_limitations")),
            },
        }

        for dt in DOC_TYPES:
            total += 1
            try:
                doc = generate_document(dt, sessions, patient_ctx, therapist, pid, "", ctx)
                issues = check_doc(doc)
                results[pid]["docs"][dt] = {"ok": not issues, "issues": issues, "err": None, "doc": doc}
                if not issues:
                    ok_count += 1
                for k in issues:
                    all_issues[k] = all_issues.get(k, 0) + 1
            except Exception as e:
                results[pid]["docs"][dt] = {"ok": False, "issues": {}, "err": str(e), "doc": ""}

    # ── 결과 테이블 ────────────────────────────────────────────────
    sep = "=" * 102
    print(sep)
    print(f"{'Patient':32} {'N':3}  {'MedNec':9} {'Legal':9} {'Chron':9} {'Appeal':9} {'FuncRp':9}")
    print(sep)

    for pid in sorted(results):
        r = results[pid]
        label = f"{pid} ({r['name']})"[:32]
        cols = []
        for dt in DOC_TYPES:
            d = r["docs"][dt]
            if d["err"]:
                cols.append("ERR      ")
            elif d["ok"]:
                cols.append("✓        ")
            else:
                tag = ",".join(k for k in d["issues"])
                cols.append(f"✗{tag[:8]}")
        print(f"{label:32} {r['n']:3}  {'  '.join(cols)}")

    print(sep)
    print(f"결과: {ok_count}/{total} 정상  ({ok_count / total * 100:.0f}%)\n")

    # ── 이슈 요약 ────────────────────────────────────────────────
    if all_issues:
        print("[ 잔여 이슈 ]")
        for tag, cnt in sorted(all_issues.items(), key=lambda x: -x[1]):
            pids_with = [
                p for p, r in results.items()
                if any(tag in d["issues"] for d in r["docs"].values())
            ]
            print(f"  {tag:8}: {cnt}건 → {', '.join(pids_with)}")
        print()
    else:
        print("[ 모든 문서 실제 데이터 사용 확인 ]\n")

    # ── verbose 모드 ─────────────────────────────────────────────
    if verbose:
        print("[ 이슈 상세 ]")
        for pid in sorted(results):
            for dt, d in results[pid]["docs"].items():
                if d["err"]:
                    print(f"  {pid} / {dt}: ERR — {d['err']}")
                elif d["issues"]:
                    for tag, phrase in d["issues"].items():
                        print(f"  {pid} / {dt}: {tag} → '{phrase[:50]}'")

    # ── functional_limitations 품질 요약 ─────────────────────────
    print("[ functional_limitations 추출 현황 ]")
    for pid in sorted(results):
        sessions = list(PatientTimeline.objects.filter(therapist=user, patient_id=pid).order_by("session_date"))
        ctx = get_clinical_context(sessions)
        fl = ctx.get("functional_limitations", [])
        status = "✓" if fl else "✗ empty"
        sample = str(fl[:2]) if fl else "-"
        print(f"  {pid:30}: {status}  {sample}")

    return ok_count, total, all_issues


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="PT 문서 생성 품질 테스트")
    parser.add_argument("--username", default="chrisnam", help="대상 계정")
    parser.add_argument("--patient",  default=None,       help="특정 patient_id만 테스트")
    parser.add_argument("--verbose",  action="store_true", help="이슈 라인 상세 출력")
    args = parser.parse_args()

    run_test(username=args.username, target_pid=args.patient, verbose=args.verbose)
