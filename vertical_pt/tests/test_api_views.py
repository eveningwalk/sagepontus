"""
REST API 엔드포인트 테스트 (views_api.py)
- /api/pt/analyze/       POST — SOAP 분석, DB 저장, 알람 반환
- /api/pt/timeline/      GET  — 세션 이력
- /api/pt/alerts/        GET  — 알람 목록
- /api/pt/alerts/<id>/acknowledge/  POST — 알람 확인
- /api/pt/waitlist/      POST — 대기자 명단 등록
"""
import pytest
from datetime import date
from unittest.mock import patch

from django.contrib.auth import get_user_model
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from vertical_pt.models import PatientTimeline, RedFlagAlert, WaitlistEntry

User = get_user_model()

# RED를 확실히 트리거하는 SOAP 텍스트
SOAP_RED = (
    "58M. Low back pain x 6 weeks, not improving. "
    "PMH: prostate cancer treated 3 years ago, cancer survivor. "
    "Night pain, wakes from sleep. No trauma."
)
# NONE을 트리거하는 SOAP 텍스트
SOAP_NONE = (
    "34M. Mechanical LBP after lifting. Pain improves with rest. "
    "No leg symptoms. Full bladder and bowel control."
)


# ── 픽스처 ────────────────────────────────────────────────────────────────────

@pytest.fixture
def user(db):
    return User.objects.create_user(username="testpt", password="pass1234")

@pytest.fixture
def other_user(db):
    return User.objects.create_user(username="other_pt", password="pass1234")

@pytest.fixture
def token(user):
    tok, _ = Token.objects.get_or_create(user=user)
    return tok

@pytest.fixture
def auth_client(token):
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
    return client

@pytest.fixture
def anon_client():
    return APIClient()

@pytest.fixture
def timeline(user, db):
    return PatientTimeline.objects.create(
        therapist=user,
        patient_id="PT-TEST-001",
        session_date=date.today(),
        soap_text=SOAP_RED,
        clinical_context={},
        extracted_symptoms={},
        critical_score=1.0,
        alarm_level="RED",
        triggered_condition="malignancy",
    )

@pytest.fixture
def alert(timeline, db):
    return RedFlagAlert.objects.create(
        timeline=timeline,
        condition="malignancy",
        alarm_level="RED",
        matched_indicators=["Cancer History"],
        score=1.0,
        trigger_label="Cancer History",
    )


# ── POST /api/pt/analyze/ ────────────────────────────────────────────────────

class TestAnalyze:
    URL = "/api/pt/analyze/"

    def _post(self, client, data):
        return client.post(self.URL, data, format="json")

    @pytest.mark.django_db
    def test_unauthenticated_returns_401(self, anon_client):
        resp = self._post(anon_client, {"soap_text": SOAP_RED, "patient_id": "PT-001"})
        assert resp.status_code in (401, 403)

    @pytest.mark.django_db
    def test_missing_soap_text_returns_400(self, auth_client):
        with patch("vertical_pt.api.views_api.extract_clinical_context", return_value={}):
            resp = self._post(auth_client, {"patient_id": "PT-001"})
        assert resp.status_code == 400

    @pytest.mark.django_db
    def test_missing_patient_id_returns_400(self, auth_client):
        with patch("vertical_pt.api.views_api.extract_clinical_context", return_value={}):
            resp = self._post(auth_client, {"soap_text": SOAP_RED})
        assert resp.status_code == 400

    @pytest.mark.django_db
    def test_red_soap_returns_200_with_alarm(self, auth_client):
        with patch("vertical_pt.api.views_api.extract_clinical_context", return_value={}):
            resp = self._post(auth_client, {"soap_text": SOAP_RED, "patient_id": "PT-001"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["alarm"] == "RED"
        assert data["condition"] == "malignancy"
        assert data["score"] > 0

    @pytest.mark.django_db
    def test_none_soap_returns_200_no_alarm(self, auth_client):
        with patch("vertical_pt.api.views_api.extract_clinical_context", return_value={}):
            resp = self._post(auth_client, {"soap_text": SOAP_NONE, "patient_id": "PT-002"})
        assert resp.status_code == 200
        assert resp.json()["alarm"] == "NONE"

    @pytest.mark.django_db
    def test_red_soap_creates_timeline_and_alert(self, auth_client, user):
        with patch("vertical_pt.api.views_api.extract_clinical_context", return_value={}):
            self._post(auth_client, {"soap_text": SOAP_RED, "patient_id": "PT-003"})
        assert PatientTimeline.objects.filter(therapist=user, patient_id="PT-003").exists()
        assert RedFlagAlert.objects.filter(timeline__patient_id="PT-003").exists()

    @pytest.mark.django_db
    def test_none_soap_creates_timeline_but_no_alert(self, auth_client, user):
        with patch("vertical_pt.api.views_api.extract_clinical_context", return_value={}):
            self._post(auth_client, {"soap_text": SOAP_NONE, "patient_id": "PT-004"})
        assert PatientTimeline.objects.filter(therapist=user, patient_id="PT-004").exists()
        assert not RedFlagAlert.objects.filter(timeline__patient_id="PT-004").exists()

    @pytest.mark.django_db
    def test_response_has_required_fields(self, auth_client):
        with patch("vertical_pt.api.views_api.extract_clinical_context", return_value={}):
            resp = self._post(auth_client, {"soap_text": SOAP_RED, "patient_id": "PT-005"})
        data = resp.json()
        for field in ("alarm", "condition", "score", "matched", "alert_id"):
            assert field in data, f"missing field: {field}"

    @pytest.mark.django_db
    def test_red_alert_id_returned(self, auth_client):
        with patch("vertical_pt.api.views_api.extract_clinical_context", return_value={}):
            resp = self._post(auth_client, {"soap_text": SOAP_RED, "patient_id": "PT-006"})
        assert resp.json()["alert_id"] is not None

    @pytest.mark.django_db
    def test_none_alert_id_is_null(self, auth_client):
        with patch("vertical_pt.api.views_api.extract_clinical_context", return_value={}):
            resp = self._post(auth_client, {"soap_text": SOAP_NONE, "patient_id": "PT-007"})
        assert resp.json()["alert_id"] is None


# ── GET /api/pt/timeline/ ─────────────────────────────────────────────────────

class TestTimeline:
    URL = "/api/pt/timeline/"

    @pytest.mark.django_db
    def test_unauthenticated_returns_401(self, anon_client):
        resp = anon_client.get(self.URL)
        assert resp.status_code in (401, 403)

    @pytest.mark.django_db
    def test_returns_own_sessions(self, auth_client, timeline):
        resp = auth_client.get(self.URL)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["patient_id"] == "PT-TEST-001"

    @pytest.mark.django_db
    def test_other_user_sessions_hidden(self, auth_client, other_user, db):
        PatientTimeline.objects.create(
            therapist=other_user,
            patient_id="PT-OTHER-001",
            session_date=date.today(),
            soap_text="other soap",
            clinical_context={},
            extracted_symptoms={},
            critical_score=0.0,
            alarm_level="NONE",
            triggered_condition="",
        )
        resp = auth_client.get(self.URL)
        assert resp.status_code == 200
        patient_ids = [s["patient_id"] for s in resp.json()]
        assert "PT-OTHER-001" not in patient_ids

    @pytest.mark.django_db
    def test_filter_by_patient_id(self, auth_client, user, db):
        PatientTimeline.objects.create(
            therapist=user, patient_id="PT-A", session_date=date.today(),
            soap_text="a", clinical_context={}, extracted_symptoms={},
            critical_score=0.0, alarm_level="NONE", triggered_condition="",
        )
        PatientTimeline.objects.create(
            therapist=user, patient_id="PT-B", session_date=date.today(),
            soap_text="b", clinical_context={}, extracted_symptoms={},
            critical_score=0.0, alarm_level="NONE", triggered_condition="",
        )
        resp = auth_client.get(self.URL + "?patient_id=PT-A")
        assert resp.status_code == 200
        assert all(s["patient_id"] == "PT-A" for s in resp.json())


# ── GET /api/pt/alerts/ ───────────────────────────────────────────────────────

class TestAlerts:
    URL = "/api/pt/alerts/"

    @pytest.mark.django_db
    def test_unauthenticated_returns_401(self, anon_client):
        resp = anon_client.get(self.URL)
        assert resp.status_code in (401, 403)

    @pytest.mark.django_db
    def test_returns_unacknowledged_by_default(self, auth_client, alert):
        resp = auth_client.get(self.URL)
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    @pytest.mark.django_db
    def test_acknowledged_alert_hidden_by_default(self, auth_client, alert):
        alert.acknowledged = True
        alert.save()
        resp = auth_client.get(self.URL)
        assert len(resp.json()) == 0

    @pytest.mark.django_db
    def test_all_param_shows_acknowledged(self, auth_client, alert):
        alert.acknowledged = True
        alert.save()
        resp = auth_client.get(self.URL + "?all=true")
        assert len(resp.json()) == 1

    @pytest.mark.django_db
    def test_other_user_alerts_hidden(self, auth_client, other_user, db):
        other_tl = PatientTimeline.objects.create(
            therapist=other_user, patient_id="PT-OTHER", session_date=date.today(),
            soap_text="soap", clinical_context={}, extracted_symptoms={},
            critical_score=1.0, alarm_level="RED", triggered_condition="malignancy",
        )
        RedFlagAlert.objects.create(
            timeline=other_tl, condition="malignancy", alarm_level="RED",
            matched_indicators=[], score=1.0,
        )
        resp = auth_client.get(self.URL)
        assert len(resp.json()) == 0


# ── POST /api/pt/alerts/<id>/acknowledge/ ────────────────────────────────────

class TestAcknowledge:
    def url(self, alert_id):
        return f"/api/pt/alerts/{alert_id}/acknowledge/"

    @pytest.mark.django_db
    def test_unauthenticated_returns_401(self, anon_client, alert):
        resp = anon_client.post(self.url(alert.id))
        assert resp.status_code in (401, 403)

    @pytest.mark.django_db
    def test_valid_alert_acknowledged(self, auth_client, alert):
        resp = auth_client.post(self.url(alert.id))
        assert resp.status_code == 200
        alert.refresh_from_db()
        assert alert.acknowledged is True
        assert alert.acknowledged_at is not None

    @pytest.mark.django_db
    def test_nonexistent_alert_returns_404(self, auth_client):
        resp = auth_client.post(self.url(99999))
        assert resp.status_code == 404

    @pytest.mark.django_db
    def test_other_user_alert_returns_404(self, auth_client, other_user, db):
        other_tl = PatientTimeline.objects.create(
            therapist=other_user, patient_id="PT-X", session_date=date.today(),
            soap_text="soap", clinical_context={}, extracted_symptoms={},
            critical_score=1.0, alarm_level="RED", triggered_condition="",
        )
        other_alert = RedFlagAlert.objects.create(
            timeline=other_tl, condition="malignancy", alarm_level="RED",
            matched_indicators=[], score=1.0,
        )
        resp = auth_client.post(self.url(other_alert.id))
        assert resp.status_code == 404


# ── POST /api/pt/waitlist/ ────────────────────────────────────────────────────

@pytest.fixture(autouse=False)
def no_resend(monkeypatch):
    """Resend API 키를 제거해 실제 이메일 전송 차단."""
    monkeypatch.delenv("RESEND_API_KEY", raising=False)


class TestWaitlist:
    URL = "/api/pt/waitlist/"

    @pytest.mark.django_db
    def test_valid_email_returns_ok(self, anon_client, no_resend):
        resp = anon_client.post(self.URL, {"email": "test@example.com"}, format="json")
        assert resp.status_code == 200
        assert resp.json().get("ok") is True

    @pytest.mark.django_db
    def test_invalid_email_returns_400(self, anon_client):
        resp = anon_client.post(self.URL, {"email": "not-an-email"}, format="json")
        assert resp.status_code == 400

    @pytest.mark.django_db
    def test_empty_email_returns_400(self, anon_client):
        resp = anon_client.post(self.URL, {"email": ""}, format="json")
        assert resp.status_code == 400

    @pytest.mark.django_db
    def test_valid_email_saved_to_db(self, anon_client, no_resend):
        anon_client.post(self.URL, {"email": "pt@clinic.com"}, format="json")
        assert WaitlistEntry.objects.filter(email="pt@clinic.com").exists()

    @pytest.mark.django_db
    def test_duplicate_email_idempotent(self, anon_client, no_resend):
        anon_client.post(self.URL, {"email": "dup@clinic.com"}, format="json")
        resp = anon_client.post(self.URL, {"email": "dup@clinic.com"}, format="json")
        assert resp.status_code == 200
        assert WaitlistEntry.objects.filter(email="dup@clinic.com").count() == 1

    @pytest.mark.django_db
    def test_email_normalized_to_lowercase(self, anon_client, no_resend):
        anon_client.post(self.URL, {"email": "PT@CLINIC.COM"}, format="json")
        assert WaitlistEntry.objects.filter(email="pt@clinic.com").exists()

    @pytest.mark.django_db
    def test_no_auth_required(self, anon_client, no_resend):
        # waitlist is AllowAny — no token needed
        resp = anon_client.post(self.URL, {"email": "open@test.com"}, format="json")
        assert resp.status_code == 200
