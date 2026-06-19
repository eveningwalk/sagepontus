"""
VPPA (vpps.py) 단위 테스트
- _strip_negations: 부정 표현 제거 로직
- _rule_match: KB synonym 매칭 (word boundary + substring)
- _regex_match: KB pattern 매칭
- extract_symptoms: 전체 파이프라인 (구조 + 통합)
"""
import pytest
from vertical_pt.engine.vpps import (
    _strip_negations,
    _rule_match,
    _regex_match,
    extract_symptoms,
    _load_kb,
)


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
