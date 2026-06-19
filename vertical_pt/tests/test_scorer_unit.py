"""
scorer._score_condition 단위 테스트
— 실제 프로토콜 파일 사용 없이 인라인 픽스처로 3가지 결정 로직 검증
"""
import pytest
from vertical_pt.engine.scorer import _score_condition


# ── 공통 헬퍼 ────────────────────────────────────────────────────────────────

def _hit(condition_ref, alarm_level, weight, label, kb_id="", category=""):
    return {
        "condition_ref": condition_ref,
        "alarm_level": alarm_level,
        "weight": weight,
        "label": label,
        "kb_id": kb_id,
        "category": category,
    }


def _proto(protocol_id, logic, threshold=None, alarm_level="RED"):
    p = {
        "protocol_id": f"rfp_{protocol_id}",
        "decision_logic": logic,
        "alarm_level": alarm_level,
    }
    if threshold:
        p["threshold"] = threshold
    return p


# ── ANY_CARDINAL (Cauda Equina) ───────────────────────────────────────────────

class TestAnyCardinal:
    PROTO = _proto("cauda_equina", "ANY_CARDINAL")

    def _hit(self, alarm, label="Symptom"):
        return _hit("cauda_equina", alarm, 1.0, label)

    def test_no_hits_returns_none(self):
        result = _score_condition(self.PROTO, [])
        assert result["alarm"] == "NONE"
        assert result["score"] == 0.0

    def test_single_red_hit_triggers_red(self):
        result = _score_condition(self.PROTO, [self._hit("RED", "Saddle Anesthesia")])
        assert result["alarm"] == "RED"
        assert result["score"] == 1.0
        assert result["trigger"] == "Saddle Anesthesia"

    def test_single_yellow_hit_gives_yellow(self):
        result = _score_condition(self.PROTO, [self._hit("YELLOW")])
        assert result["alarm"] == "YELLOW"
        assert result["score"] == 0.5

    def test_two_yellow_hits_escalate_to_red(self):
        hits = [self._hit("YELLOW", "Symptom A"), self._hit("YELLOW", "Symptom B")]
        result = _score_condition(self.PROTO, hits)
        assert result["alarm"] == "RED"
        assert result["score"] == 0.9

    def test_matched_labels_included(self):
        hits = [self._hit("RED", "Bladder Dysfunction")]
        result = _score_condition(self.PROTO, hits)
        assert "Bladder Dysfunction" in result["matched"]

    def test_unrelated_hits_ignored(self):
        hits = [_hit("malignancy", "RED", 1.0, "Cancer")]
        result = _score_condition(self.PROTO, hits)
        assert result["alarm"] == "NONE"


# ── SCREEN_OF_5 (Malignancy) ─────────────────────────────────────────────────

class TestScreenOf5:
    PROTO = _proto("malignancy", "SCREEN_OF_5", threshold={"red": 4, "yellow": 2})

    def _hit(self, label="Item", kb_id="", alarm="YELLOW"):
        return _hit("malignancy", alarm, 0.6, label, kb_id=kb_id)

    def test_cancer_history_rf009_alone_triggers_red(self):
        result = _score_condition(self.PROTO, [self._hit("Cancer History", kb_id="RF_009")])
        assert result["alarm"] == "RED"
        assert result["score"] == 1.0

    def test_four_items_triggers_red(self):
        hits = [self._hit(f"Item {i}") for i in range(4)]
        result = _score_condition(self.PROTO, hits)
        assert result["alarm"] == "RED"

    def test_two_items_gives_yellow(self):
        hits = [self._hit(f"Item {i}") for i in range(2)]
        result = _score_condition(self.PROTO, hits)
        assert result["alarm"] == "YELLOW"

    def test_one_item_gives_none(self):
        hits = [self._hit("Single Item")]
        result = _score_condition(self.PROTO, hits)
        assert result["alarm"] == "NONE"

    def test_score_proportional_to_count(self):
        hits = [self._hit(f"Item {i}") for i in range(3)]
        result = _score_condition(self.PROTO, hits)
        assert result["score"] == pytest.approx(3 / 5.0, abs=0.01)


# ── WEIGHTED_SUM (Vascular / Fracture) ───────────────────────────────────────

class TestWeightedSum:
    PROTO = _proto("vascular", "WEIGHTED_SUM", threshold={"red": 0.70, "yellow": 0.45})
    FRACTURE_PROTO = _proto("fracture", "WEIGHTED_SUM", threshold={"red": 0.70, "yellow": 0.45})

    def _hit(self, condition, alarm, weight, label="Symptom", category=""):
        return _hit(condition, alarm, weight, label, category=category)

    def test_high_weight_red_indicator_triggers_immediately(self):
        hit = self._hit("vascular", "RED", 0.95, "Pulsating Mass")
        result = _score_condition(self.PROTO, [hit])
        assert result["alarm"] == "RED"
        assert result["score"] == 1.0

    def test_weight_095_boundary_triggers_immediate_red(self):
        hit = self._hit("vascular", "RED", 0.95, "Boundary")
        result = _score_condition(self.PROTO, [hit])
        assert result["alarm"] == "RED"

    def test_weight_094_does_not_trigger_immediately(self):
        hit = self._hit("vascular", "RED", 0.94, "Near Boundary")
        result = _score_condition(self.PROTO, [hit])
        # 0.94 < red threshold 0.70? 0.94 >= 0.70 so should be RED via sum
        assert result["alarm"] == "RED"
        assert result["score"] != 1.0  # sum path, not immediate path

    def test_sum_above_red_threshold_gives_red(self):
        hits = [
            self._hit("vascular", "RED", 0.4, "Symptom A"),
            self._hit("vascular", "YELLOW", 0.4, "Symptom B"),
        ]
        result = _score_condition(self.PROTO, hits)
        assert result["alarm"] == "RED"

    def test_sum_between_thresholds_gives_yellow(self):
        hit = self._hit("vascular", "YELLOW", 0.55, "Single Symptom")
        result = _score_condition(self.PROTO, [hit])
        assert result["alarm"] == "YELLOW"

    def test_sum_below_yellow_threshold_gives_none(self):
        hit = self._hit("vascular", "YELLOW", 0.3, "Weak Signal")
        result = _score_condition(self.PROTO, [hit])
        assert result["alarm"] == "NONE"

    def test_score_capped_at_1(self):
        hits = [self._hit("vascular", "RED", 0.7, f"S{i}") for i in range(3)]
        result = _score_condition(self.PROTO, hits)
        assert result["score"] <= 1.0

    def test_fracture_without_trauma_label_downgraded_to_yellow(self):
        # 외상력 없이 weight sum이 RED 임계치 초과 → YELLOW로 하향
        hits = [
            self._hit("fracture", "YELLOW", 0.65, "Osteoporosis"),
            self._hit("fracture", "YELLOW", 0.70, "Steroid Use"),
        ]
        result = _score_condition(self.FRACTURE_PROTO, hits)
        assert result["alarm"] == "YELLOW"

    def test_fracture_with_trauma_label_stays_red(self):
        hits = [
            self._hit("fracture", "RED", 0.8, "Significant Trauma"),
            self._hit("fracture", "YELLOW", 0.65, "Osteoporosis"),
        ]
        result = _score_condition(self.FRACTURE_PROTO, hits)
        assert result["alarm"] == "RED"
