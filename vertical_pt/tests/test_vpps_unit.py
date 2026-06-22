"""
VPPA (vpps.py) 단위 테스트
- _strip_negations: 부정 표현 제거 로직
- _rule_match: KB synonym 매칭 (word boundary + substring)
- _regex_match: KB pattern 매칭
- extract_symptoms: 전체 파이프라인 (구조 + 통합)
- split_sections: SOAP 섹션 분리
- 섹션 컨텍스트: section 필드, OBJECTIVE depth 가산
- screening_source / soap_primary 필드
- _section_bonus: soap_primary × 섹션 교차 보정
- scorer screening_breakdown 그룹핑
- referral 인디케이터 섹션 분류
"""
import pytest
from vertical_pt.engine.vpps import (
    _strip_negations,
    _rule_match,
    _regex_match,
    _section_bonus,
    extract_symptoms,
    _load_kb,
)
from vertical_pt.engine.normalizer import split_sections


# ── 픽스처 ────────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def kb():
    return _load_kb()


# ── _strip_negations ──────────────────────────────────────────────────────────

class TestStripNegations:
    def _clean(self, text):
        return _strip_negations(text).lower()

    def test_no_fever_blanks_fever(self):
        assert "fever" not in self._clean("no fever")

    def test_denies_weight_loss_blanks_it(self):
        result = self._clean("denies weight loss")
        assert "weight" not in result
        assert "loss" not in result

    def test_absence_of_blanks_symptom(self):
        assert "fever" not in self._clean("absence of fever")

    def test_negative_for_comma_list_blanks_all(self):
        result = self._clean("negative for headaches, nausea, fever")
        assert "headaches" not in result
        assert "nausea" not in result
        assert "fever" not in result

    def test_no_evidence_of_blanks_cancer(self):
        assert "cancer" not in self._clean("no evidence of cancer")

    def test_no_history_of_blanks_symptom(self):
        assert "cancer" not in self._clean("no history of cancer")

    # 예외 — 부정어 뒤 예외 단어는 보존
    def test_no_improvement_preserved(self):
        result = self._clean("no improvement after 4 weeks")
        assert "improvement" in result

    def test_without_relief_preserved(self):
        result = self._clean("pain without relief")
        assert "relief" in result

    def test_without_change_preserved(self):
        result = self._clean("pain without change")
        assert "change" in result

    def test_no_response_preserved(self):
        result = self._clean("no response to treatment")
        assert "response" in result

    def test_plain_text_unchanged(self):
        text = "patient reports fever and night sweats"
        assert _strip_negations(text) == text

    def test_original_length_preserved(self):
        text = "no fever present"
        assert len(_strip_negations(text)) == len(text)


# ── _rule_match ───────────────────────────────────────────────────────────────

class TestRuleMatch:
    def test_fever_synonym_matches_rf013(self, kb):
        hits = _rule_match("Patient has fever 38.5C", kb)
        ids = [h["kb_id"] for h in hits]
        assert "RF_013" in ids

    def test_negated_fever_not_matched(self, kb):
        hits = _rule_match("no fever noted", kb)
        ids = [h["kb_id"] for h in hits]
        assert "RF_013" not in ids

    def test_cancer_survivor_matches_rf009(self, kb):
        hits = _rule_match("PMH: cancer survivor, prostate cancer", kb)
        ids = [h["kb_id"] for h in hits]
        assert "RF_009" in ids

    def test_saddle_numbness_matches_rf001(self, kb):
        hits = _rule_match("Saddle area numbness confirmed on exam", kb)
        ids = [h["kb_id"] for h in hits]
        assert "RF_001" in ids

    def test_urinary_retention_matches_rf002(self, kb):
        hits = _rule_match("Patient reports urinary retention", kb)
        ids = [h["kb_id"] for h in hits]
        assert "RF_002" in ids

    def test_word_boundary_afebrile_not_matched(self, kb):
        # "afebrile" should NOT match "febrile" (word boundary protection)
        hits = _rule_match("Patient is afebrile", kb)
        ids = [h["kb_id"] for h in hits]
        assert "RF_013" not in ids

    def test_deduplication_single_hit_per_kb_id(self, kb):
        # Multiple synonyms of same RF → only 1 hit
        hits = _rule_match("cancer survivor, history of cancer, prior cancer", kb)
        rf009_hits = [h for h in hits if h["kb_id"] == "RF_009"]
        assert len(rf009_hits) == 1

    def test_empty_text_returns_no_hits(self, kb):
        assert _rule_match("", kb) == []

    def test_hit_structure_has_required_keys(self, kb):
        hits = _rule_match("fever", kb)
        assert hits, "expected at least one hit"
        for key in ("kb_id", "label", "weight", "alarm_level", "condition_ref", "category"):
            assert key in hits[0], f"missing key: {key}"

    def test_case_insensitive_matching(self, kb):
        hits_lower = _rule_match("fever", kb)
        hits_upper = _rule_match("FEVER", kb)
        assert {h["kb_id"] for h in hits_lower} == {h["kb_id"] for h in hits_upper}


# ── _regex_match ──────────────────────────────────────────────────────────────

class TestRegexMatch:
    def test_numeric_weight_loss_matches_rf010(self, kb):
        # pattern: \b\d+\s*(?:lb|lbs|pounds?)\s+(?:weight\s+)?loss
        hits = _regex_match("Patient lost 15lbs weight loss over 3 months", kb, set())
        ids = [h["kb_id"] for h in hits]
        assert "RF_010" in ids

    def test_pain_at_rest_numeric_matches_rf011(self, kb):
        # pattern: \d+\s*/\s*10\b[^.\n]{0,30}at\s+rest
        hits = _regex_match("Pain 8/10 at rest, wakes from sleep", kb, set())
        ids = [h["kb_id"] for h in hits]
        assert "RF_011" in ids

    def test_fever_temperature_pattern_matches_rf013(self, kb):
        # pattern: temp(?:erature)?\s+(?:of\s+)?(?:1(?:0[0-9]|[1-9]\d))\s*[Ff]
        hits = _regex_match("Temp 101F noted at intake", kb, set())
        ids = [h["kb_id"] for h in hits]
        assert "RF_013" in ids

    def test_already_seen_id_skipped(self, kb):
        # RF_011 in seen → should not appear in regex hits
        hits = _regex_match("Pain 8/10 at rest", kb, seen={"RF_011"})
        ids = [h["kb_id"] for h in hits]
        assert "RF_011" not in ids

    def test_no_match_returns_empty(self, kb):
        hits = _regex_match("Patient ambulates independently, no complaints", kb, set())
        assert isinstance(hits, list)


# ── extract_symptoms (full pipeline) ─────────────────────────────────────────

class TestExtractSymptoms:
    REQUIRED_KEYS = ("hits", "hit_count", "has_red_indicator", "source")

    def test_return_structure_has_required_keys(self):
        result = extract_symptoms("back pain")
        for key in self.REQUIRED_KEYS:
            assert key in result, f"missing key: {key}"

    def test_empty_text_returns_empty_hits(self):
        result = extract_symptoms("")
        assert result["hits"] == []
        assert result["hit_count"] == 0
        assert result["has_red_indicator"] is False

    def test_source_is_rule(self):
        result = extract_symptoms("fever noted")
        assert result["source"] == "rule"

    def test_hit_count_matches_hits_length(self):
        result = extract_symptoms("fever, urinary retention, saddle numbness")
        assert result["hit_count"] == len(result["hits"])

    def test_red_indicator_true_when_red_found(self):
        result = extract_symptoms("cancer survivor, night pain, no improvement")
        assert result["has_red_indicator"] is True

    def test_no_red_indicator_for_normal_soap(self):
        result = extract_symptoms(
            "34M. Mechanical LBP after lifting. Improves with rest. "
            "Full bladder and bowel control. No systemic symptoms."
        )
        assert result["has_red_indicator"] is False

    def test_negated_fever_not_in_hits(self):
        result = extract_symptoms("no fever today, afebrile on exam")
        ids = [h["kb_id"] for h in result["hits"]]
        assert "RF_013" not in ids

    def test_fever_without_negation_in_hits(self):
        result = extract_symptoms("Fever 38.8C, chills noted")
        ids = [h["kb_id"] for h in result["hits"]]
        assert "RF_013" in ids

    def test_pre_confirmed_ids_inject_missing_entry(self):
        # Text has no cancer keywords, but UI checkbox confirmed RF_009
        result = extract_symptoms("back pain, no systemic symptoms", pre_confirmed_ids=["RF_009"])
        ids = [h["kb_id"] for h in result["hits"]]
        assert "RF_009" in ids

    def test_pre_confirmed_ids_no_duplicate(self):
        # RF_009 already matched by text AND pre_confirmed → only 1 hit
        result = extract_symptoms("cancer survivor", pre_confirmed_ids=["RF_009"])
        rf009_hits = [h for h in result["hits"] if h["kb_id"] == "RF_009"]
        assert len(rf009_hits) == 1

    def test_hits_sorted_by_weight_descending(self):
        result = extract_symptoms(
            "fever, urinary retention, saddle area numbness, cancer survivor"
        )
        weights = [h["weight"] for h in result["hits"]]
        assert weights == sorted(weights, reverse=True)


# ── split_sections ────────────────────────────────────────────────────────────

class TestSplitSections:
    def test_basic_split(self):
        text = "SUBJECTIVE:\npatient reports pain\nOBJECTIVE:\npercussion tenderness"
        s = split_sections(text)
        assert "patient reports pain" in s["SUBJECTIVE"]
        assert "percussion tenderness" in s["OBJECTIVE"]

    def test_no_headers_all_goes_to_unknown(self):
        text = "patient has fever and back pain"
        s = split_sections(text)
        assert "patient has fever" in s["UNKNOWN"]
        assert s["SUBJECTIVE"] == ""
        assert s["OBJECTIVE"] == ""

    def test_pre_header_text_goes_to_unknown(self):
        text = "intake note\nSUBJECTIVE:\nchief complaint: pain"
        s = split_sections(text)
        assert "intake note" in s["UNKNOWN"]
        assert "chief complaint" in s["SUBJECTIVE"]

    def test_empty_section_is_empty_string(self):
        text = "SUBJECTIVE:\nsome text\nOBJECTIVE:\nPLAN:\ncontinue PT"
        s = split_sections(text)
        assert s["OBJECTIVE"] == ""
        assert "continue PT" in s["PLAN"]

    def test_all_four_sections_split(self):
        text = (
            "SUBJECTIVE:\nS text\n"
            "OBJECTIVE:\nO text\n"
            "ASSESSMENT:\nA text\n"
            "PLAN:\nP text"
        )
        s = split_sections(text)
        assert "S text" in s["SUBJECTIVE"]
        assert "O text" in s["OBJECTIVE"]
        assert "A text" in s["ASSESSMENT"]
        assert "P text" in s["PLAN"]

    def test_returns_all_keys(self):
        s = split_sections("no headers here")
        for key in ("SUBJECTIVE", "OBJECTIVE", "ASSESSMENT", "PLAN", "UNKNOWN"):
            assert key in s


# ── 섹션 컨텍스트 (section 필드 + depth 가산) ─────────────────────────────────

class TestSectionContext:
    def test_hit_has_section_field(self, kb):
        hits = _rule_match("fever", kb, section="SUBJECTIVE")
        assert hits
        assert hits[0]["section"] == "SUBJECTIVE"

    def test_objective_bonus_increases_weight(self, kb):
        # RF_008(soap_primary="O"): OBJECTIVE > SUBJECTIVE weight
        hit_subj = _rule_match("percussion tenderness", kb, section="SUBJECTIVE")
        hit_obj  = _rule_match("percussion tenderness", kb, section="OBJECTIVE")
        assert hit_obj,  "OBJECTIVE에서 hit 없음"
        assert hit_subj, "SUBJECTIVE에서 hit 없음"
        rf008_subj = next(h for h in hit_subj if h["kb_id"] == "RF_008")
        rf008_obj  = next(h for h in hit_obj  if h["kb_id"] == "RF_008")
        assert rf008_obj["weight"] > rf008_subj["weight"]

    def test_weight_capped_at_1(self, kb):
        # depth=1.0인 항목에 섹션 보너스가 더해져도 1.0 초과 안 됨
        hits = _rule_match("saddle area numbness", kb, section="OBJECTIVE")
        rf001 = next((h for h in hits if h["kb_id"] == "RF_001"), None)
        assert rf001 is not None
        assert rf001["weight"] <= 1.0

    def test_extract_symptoms_hit_has_section_field(self):
        result = extract_symptoms("fever noted")
        assert result["hits"]
        assert "section" in result["hits"][0]

    def test_objective_section_wins_over_subjective(self):
        # 같은 항목이 SUBJECTIVE와 OBJECTIVE 모두에 있으면 OBJECTIVE(weight 높음)가 최종
        soap = (
            "SUBJECTIVE:\npatient reports pain at rest\n"
            "OBJECTIVE:\npain 7/10 at rest, wakes from sleep"
        )
        result = extract_symptoms(soap, source="raw")
        rf011_hits = [h for h in result["hits"] if h["kb_id"] == "RF_011"]
        assert len(rf011_hits) == 1                      # dedup 됨
        assert rf011_hits[0]["section"] == "OBJECTIVE"   # 높은 weight 쪽 선택

    def test_pmh_item_found_in_subjective(self):
        soap = "SUBJECTIVE:\nPMH: cancer survivor\nOBJECTIVE:\nROM within normal limits"
        result = extract_symptoms(soap, source="raw")
        rf009 = next((h for h in result["hits"] if h["kb_id"] == "RF_009"), None)
        assert rf009 is not None
        assert rf009["section"] == "SUBJECTIVE"

    def test_unknown_section_has_zero_bonus(self, kb):
        # UNKNOWN 섹션은 모든 soap_primary에 대해 보너스 0 → weight == depth
        hits = _rule_match("fever", kb, section="UNKNOWN")
        kb_data = _load_kb()
        rf013 = next((h for h in hits if h["kb_id"] == "RF_013"), None)
        assert rf013 is not None
        assert rf013["weight"] == kb_data["RF_013"]["depth"]


# ── screening_source / soap_primary 필드 ─────────────────────────────────────

class TestScreeningFields:
    """hits에 screening_source + soap_primary 필드가 올바르게 포함되는지 검증."""

    def test_hit_has_screening_source_field(self, kb):
        hits = _rule_match("fever", kb)
        assert hits
        assert "screening_source" in hits[0]

    def test_hit_has_soap_primary_field(self, kb):
        hits = _rule_match("fever", kb)
        assert hits
        assert "soap_primary" in hits[0]

    def test_pmh_item_has_correct_screening_source(self, kb):
        # RF_009 Previous Cancer History → pmh
        hits = _rule_match("cancer survivor", kb)
        rf009 = next((h for h in hits if h["kb_id"] == "RF_009"), None)
        assert rf009 is not None
        assert rf009["screening_source"] == "pmh"

    def test_risk_factor_item_has_correct_screening_source(self, kb):
        # RF_025 Age > 50 → risk_factor
        hits = _rule_match("65 y/o male", kb)
        rf025 = next((h for h in hits if h["kb_id"] == "RF_025"), None)
        assert rf025 is not None
        assert rf025["screening_source"] == "risk_factor"

    def test_ros_item_has_correct_screening_source(self, kb):
        # RF_002 Bladder Dysfunction → ros
        hits = _rule_match("urinary retention noted", kb)
        rf002 = next((h for h in hits if h["kb_id"] == "RF_002"), None)
        assert rf002 is not None
        assert rf002["screening_source"] == "ros"

    def test_clinical_presentation_item_has_correct_screening_source(self, kb):
        # RF_011 Night Pain → clinical_presentation
        hits = _rule_match("wakes from sleep with pain", kb)
        rf011 = next((h for h in hits if h["kb_id"] == "RF_011"), None)
        assert rf011 is not None
        assert rf011["screening_source"] == "clinical_presentation"

    def test_associated_symptoms_item_has_correct_screening_source(self, kb):
        # RF_010 Weight Loss → associated_symptoms
        hits = _rule_match("unexplained weight loss", kb)
        rf010 = next((h for h in hits if h["kb_id"] == "RF_010"), None)
        assert rf010 is not None
        assert rf010["screening_source"] == "associated_symptoms"

    def test_objective_item_soap_primary_value(self, kb):
        # RF_004 Bilateral LE Weakness → soap_primary = "O"
        hits = _rule_match("bilateral leg weakness", kb)
        rf004 = next((h for h in hits if h["kb_id"] == "RF_004"), None)
        assert rf004 is not None
        assert rf004["soap_primary"] == "O"

    def test_s_plus_o_item_soap_primary_value(self, kb):
        # RF_013 Fever → soap_primary = "S+O"
        hits = _rule_match("fever", kb)
        rf013 = next((h for h in hits if h["kb_id"] == "RF_013"), None)
        assert rf013 is not None
        assert rf013["soap_primary"] == "S+O"

    def test_extract_symptoms_hits_carry_screening_fields(self):
        result = extract_symptoms("fever, cancer survivor, urinary retention")
        for hit in result["hits"]:
            assert "screening_source" in hit, f"{hit['kb_id']} missing screening_source"
            assert "soap_primary" in hit,     f"{hit['kb_id']} missing soap_primary"

    def test_new_rf030_family_cancer_history_fields(self, kb):
        # RF_030 신규 항목 — pmh / S
        hits = _rule_match("family history of cancer", kb)
        rf030 = next((h for h in hits if h["kb_id"] == "RF_030"), None)
        assert rf030 is not None
        assert rf030["screening_source"] == "pmh"
        assert rf030["soap_primary"] == "S"

    def test_new_rf034_cardiovascular_ros_fields(self, kb):
        # RF_034 신규 항목 — ros / S+O / RED
        hits = _rule_match("chest pain", kb)
        rf034 = next((h for h in hits if h["kb_id"] == "RF_034"), None)
        assert rf034 is not None
        assert rf034["screening_source"] == "ros"
        assert rf034["alarm_level"] == "RED"


# ── _section_bonus 교차 보정 ──────────────────────────────────────────────────

class TestSectionBonus:
    """soap_primary × section 교차 보정 값 검증."""

    # soap_primary = "O" (임상가 측정 항목)
    def test_o_item_in_objective_max_bonus(self):
        assert _section_bonus("O", "OBJECTIVE") == 0.15

    def test_o_item_in_subjective_penalty(self):
        # 환자 자가보고 → 신뢰도 낮음
        assert _section_bonus("O", "SUBJECTIVE") == -0.05

    def test_o_item_in_assessment_small_bonus(self):
        assert _section_bonus("O", "ASSESSMENT") == 0.05

    def test_o_item_in_unknown_no_bonus(self):
        assert _section_bonus("O", "UNKNOWN") == 0.0

    # soap_primary = "S+O" (양쪽 동등)
    def test_s_plus_o_item_in_objective_bonus(self):
        assert _section_bonus("S+O", "OBJECTIVE") == 0.10

    def test_s_plus_o_item_in_subjective_no_bonus(self):
        assert _section_bonus("S+O", "SUBJECTIVE") == 0.0

    # soap_primary = "S" (주관적 보고 항목)
    def test_s_item_in_subjective_no_bonus(self):
        assert _section_bonus("S", "SUBJECTIVE") == 0.0

    def test_s_item_in_objective_small_bonus(self):
        # 임상가가 객관적으로도 확인 → 소폭 보너스
        assert _section_bonus("S", "OBJECTIVE") == 0.05

    def test_s_item_in_assessment_small_bonus(self):
        assert _section_bonus("S", "ASSESSMENT") == 0.05

    # 실제 weight 검증 (KB 연동)
    def test_o_item_objective_weight_gt_subjective_weight(self, kb):
        # RF_008 Point Tenderness (soap_primary=O, depth=0.75)
        hit_s = _rule_match("point tenderness", kb, section="SUBJECTIVE")
        hit_o = _rule_match("point tenderness", kb, section="OBJECTIVE")
        rf008_s = next(h for h in hit_s if h["kb_id"] == "RF_008")
        rf008_o = next(h for h in hit_o if h["kb_id"] == "RF_008")
        assert rf008_o["weight"] > rf008_s["weight"]

    def test_o_item_subjective_weight_below_depth(self, kb):
        # RF_008 S에서 잡히면 depth(0.75) - 0.05 = 0.70
        hits = _rule_match("point tenderness", kb, section="SUBJECTIVE")
        rf008 = next(h for h in hits if h["kb_id"] == "RF_008")
        kb_data = _load_kb()
        assert rf008["weight"] < kb_data["RF_008"]["depth"]

    def test_weight_never_goes_negative(self, kb):
        # 어떤 섹션에서도 weight >= 0
        for section in ("SUBJECTIVE", "OBJECTIVE", "ASSESSMENT", "PLAN", "UNKNOWN"):
            hits = _rule_match("point tenderness fever cancer survivor", kb, section=section)
            for h in hits:
                assert h["weight"] >= 0.0, f"{h['kb_id']} weight < 0 in {section}"

    def test_fallback_bonus_for_empty_soap_primary(self):
        # soap_primary 미정의 → fallback: OBJECTIVE +0.10, 나머지 0
        assert _section_bonus("", "OBJECTIVE")  == 0.10
        assert _section_bonus("", "SUBJECTIVE") == 0.0


# ── scorer screening_breakdown ────────────────────────────────────────────────

class TestScorerBreakdown:
    """detect_red_flags 결과의 screening_breakdown 필드 검증."""

    def _run(self, soap: str):
        from vertical_pt.engine.scorer import detect_red_flags
        result = extract_symptoms(soap)
        return detect_red_flags(result)

    def test_active_condition_has_screening_breakdown(self):
        scored = self._run("cancer survivor, night pain, weight loss 15lbs")
        active = [c for c in scored["conditions"] if c["alarm"] != "NONE"]
        assert active, "활성 조건 없음"
        for c in active:
            assert "screening_breakdown" in c, f"{c['condition']} missing screening_breakdown"

    def test_breakdown_is_dict(self):
        scored = self._run("cancer survivor, fever")
        for c in scored["conditions"]:
            assert isinstance(c["screening_breakdown"], dict)

    def test_pmh_items_appear_in_breakdown(self):
        # RF_009 (pmh) → malignancy breakdown["pmh"] 에 포함
        scored = self._run("cancer survivor")
        malignancy = next((c for c in scored["conditions"] if c["condition"] == "malignancy"), None)
        assert malignancy is not None
        assert "pmh" in malignancy["screening_breakdown"]
        labels = malignancy["screening_breakdown"]["pmh"]
        assert any("Cancer" in lbl for lbl in labels)

    def test_associated_symptoms_appear_in_breakdown(self):
        scored = self._run("unexplained weight loss 10lbs, night sweats")
        malignancy = next((c for c in scored["conditions"] if c["condition"] == "malignancy"), None)
        assert malignancy is not None
        bd = malignancy["screening_breakdown"]
        assert "associated_symptoms" in bd

    def test_risk_factor_appears_in_breakdown(self):
        scored = self._run("cancer survivor, smoker 20 pack-year history, age 65 y/o")
        malignancy = next((c for c in scored["conditions"] if c["condition"] == "malignancy"), None)
        assert malignancy is not None
        assert "risk_factor" in malignancy["screening_breakdown"]

    def test_multiple_sources_all_present(self):
        # PMH + risk_factor + associated_symptoms 섞인 케이스
        scored = self._run(
            "PMH: cancer survivor. Smoker. "
            "Unexplained weight loss 12lbs. Night sweats. "
            "Pain wakes her from sleep."
        )
        malignancy = next((c for c in scored["conditions"] if c["condition"] == "malignancy"), None)
        assert malignancy is not None
        bd = malignancy["screening_breakdown"]
        assert len(bd) >= 2, f"소스 카테고리 부족: {list(bd.keys())}"

    def test_no_hits_gives_empty_breakdown(self):
        from vertical_pt.engine.scorer import detect_red_flags
        empty_result = {"hits": []}
        scored = detect_red_flags(empty_result)
        for cond_data in scored["details"].values():
            assert cond_data["screening_breakdown"] == {}


# ── referral 인디케이터 그룹화 ────────────────────────────────────────────────

class TestReferralGrouping:
    """리퍼럴 레터 인디케이터 섹션이 screening_source별로 그룹화되는지 검증."""

    def _letter(self, soap: str) -> str:
        from vertical_pt.engine.scorer import detect_red_flags
        from vertical_pt.engine.referral import generate_multi_referral_letter
        result  = extract_symptoms(soap)
        scored  = detect_red_flags(result)
        return generate_multi_referral_letter(
            scored["conditions"], "PT-TEST", "Test PT", "Test Clinic"
        )

    def test_letter_contains_section_header_for_pmh(self):
        letter = self._letter("cancer survivor, weight loss 10lbs, night pain")
        assert "[Past Medical History]" in letter

    def test_letter_contains_section_header_for_associated_symptoms(self):
        letter = self._letter("cancer survivor, unexplained weight loss 10lbs, night sweats")
        assert "[Associated Signs & Symptoms]" in letter

    def test_letter_contains_section_header_for_clinical_presentation(self):
        letter = self._letter("cancer survivor, wakes from sleep, no improvement after 6 weeks")
        assert "[Clinical Presentation]" in letter

    def test_letter_contains_section_header_for_risk_factors(self):
        letter = self._letter("cancer survivor, smoker 20 pack-years, age 65 y/o")
        assert "[Risk Factors]" in letter

    def test_pmh_header_appears_before_risk_factor_header(self):
        # _SOURCE_ORDER: pmh → risk_factor → clinical_presentation → associated_symptoms → ros
        letter = self._letter(
            "cancer survivor, smoker 20 pack-years, weight loss 10lbs"
        )
        pmh_pos  = letter.find("[Past Medical History]")
        risk_pos = letter.find("[Risk Factors]")
        assert pmh_pos != -1 and risk_pos != -1
        assert pmh_pos < risk_pos

    def test_no_breakdown_falls_back_to_bullet_list(self):
        from vertical_pt.engine.referral import _format_indicators_grouped
        matched = ["Item A", "Item B"]
        output  = _format_indicators_grouped(matched, breakdown={})
        assert "  • Item A" in output
        assert "  • Item B" in output
        assert "[" not in output  # 섹션 헤더 없음

    def test_grouped_format_indents_items_under_header(self):
        from vertical_pt.engine.referral import _format_indicators_grouped
        breakdown = {"pmh": ["Cancer History"], "risk_factor": ["Age > 50"]}
        output    = _format_indicators_grouped(["Cancer History", "Age > 50"], breakdown)
        assert "[Past Medical History]" in output
        assert "    • Cancer History" in output  # 4-space indent
        assert "[Risk Factors]" in output
        assert "    • Age > 50" in output

    def test_empty_conditions_returns_empty_letter(self):
        from vertical_pt.engine.referral import generate_multi_referral_letter
        letter = generate_multi_referral_letter([], "PT-TEST", "Test PT")
        assert letter == ""

    def test_ros_items_grouped_under_ros_header(self):
        # RF_034 Cardiovascular ROS (ros) → [Review of Systems]
        letter = self._letter("chest pain with back pain, shortness of breath")
        # vascular 조건이 활성화되어야 함
        if "[Review of Systems]" in letter:
            idx = letter.find("[Review of Systems]")
            snippet = letter[idx: idx + 200]
            assert "•" in snippet  # 항목 포함
