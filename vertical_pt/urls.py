from django.urls import path
from .api import views_api
from .views import views_pt_alarm, views_pt_auth

app_name = "vertical_pt"

urlpatterns = [
    # ── PT 전용 인증 ──────────────────────────────────────────────────────
    path("pt/signup/", views_pt_auth.pt_signup, name="pt_signup"),
    path("pt/login/",  views_pt_auth.pt_login,  name="pt_login"),
    path("pt/logout/", views_pt_auth.pt_logout, name="pt_logout"),

    # ── REST API (Chrome Extension / 외부 클라이언트) ─────────────────────
    path("api/pt/analyze/",                  views_api.analyze,           name="analyze"),
    path("api/pt/timeline/",                 views_api.patient_timeline,  name="timeline"),
    path("api/pt/alerts/",                   views_api.alerts_list,       name="alerts"),
    path("api/pt/alerts/<int:alert_id>/acknowledge/", views_api.acknowledge_alert, name="acknowledge"),

    # ── 사이드바 앱 AJAX 엔드포인트 ──────────────────────────────────────
    path("pt/api/alarms/",                   views_pt_alarm.alarm_dashboard_json,  name="pt_alarms"),
    path("pt/api/save/",                     views_pt_alarm.save_soap_ajax,        name="pt_save"),
    path("pt/api/patients/",                 views_pt_alarm.patient_list_json,     name="pt_patients"),
    path("pt/api/patients/<str:patient_id>/sessions/",
                                             views_pt_alarm.patient_sessions_json, name="pt_patient_sessions"),
    path("pt/api/sessions/<int:session_id>/delete/",
                                             views_pt_alarm.delete_session,        name="pt_session_delete"),
    path("pt/api/generate-patient-id/",      views_pt_alarm.generate_patient_id,  name="pt_generate_pid"),

    # ── 웹 UI ─────────────────────────────────────────────────────────────
    path("pt/",          views_pt_alarm.index,        name="pt_index"),
    path("pt/analyze/",  views_pt_alarm.analyze_view, name="pt_analyze"),
    path("pt/result/",   views_pt_alarm.result_view,  name="pt_result"),
]
