from django.urls import path
from .api import views_api
from .views import views_pt_alarm, views_pt_auth

app_name = "vertical_pt"

urlpatterns = [
    # ── PT 전용 인증 ──────────────────────────────────────────────────────
    path("pt/signup/",            views_pt_auth.pt_signup,     name="pt_signup"),
    path("pt/login/",             views_pt_auth.pt_login,      name="pt_login"),
    path("pt/logout/",            views_pt_auth.pt_logout,     name="pt_logout"),
    path("pt/api/check-email/",   views_pt_auth.check_email,   name="pt_check_email"),

    # ── REST API (Chrome Extension / 외부 클라이언트) ─────────────────────
    path("api/pt/analyze/",                  views_api.analyze,           name="analyze"),
    path("api/pt/timeline/",                 views_api.patient_timeline,  name="timeline"),
    path("api/pt/alerts/",                   views_api.alerts_list,       name="alerts"),
    path("api/pt/alerts/<int:alert_id>/acknowledge/", views_api.acknowledge_alert, name="acknowledge"),
    path("api/pt/alerts/<int:alert_id>/referral/",   views_api.generate_referral,  name="api_referral"),
    path("api/pt/alerts/<int:alert_id>/action/",     views_api.alarm_action,       name="api_alarm_action"),

    # ── 사이드바 앱 AJAX 엔드포인트 ──────────────────────────────────────
    path("pt/api/alarms/",                   views_pt_alarm.alarm_dashboard_json,  name="pt_alarms"),
    path("pt/api/save/",                     views_pt_alarm.save_soap_ajax,        name="pt_save"),
    path("pt/api/patients/",                 views_pt_alarm.patient_list_json,     name="pt_patients"),
    path("pt/api/patients/<str:patient_id>/sessions/",
                                             views_pt_alarm.patient_sessions_json, name="pt_patient_sessions"),
    path("pt/api/sessions/<int:session_id>/delete/",
                                             views_pt_alarm.delete_session,        name="pt_session_delete"),
    path("pt/api/sessions/<int:session_id>/overrides/",
                                             views_pt_alarm.save_section_overrides, name="pt_section_overrides"),
    path("pt/api/generate-patient-id/",      views_pt_alarm.generate_patient_id,  name="pt_generate_pid"),
    path("pt/api/patients/<str:patient_id>/generate-doc/",
                                             views_pt_alarm.generate_doc_ajax,    name="pt_generate_doc"),
    path("pt/api/docs/<int:doc_id>/choose/",
                                             views_pt_alarm.choose_doc_version,   name="pt_doc_choose"),
    path("pt/api/transcribe/",               views_pt_alarm.transcribe_audio,     name="pt_transcribe"),

    # ── 리퍼럴 추적 Phase 1 ────────────────────────────────────────
    path("pt/api/alerts/<int:alert_id>/generate/",   views_pt_alarm.referral_generate,  name="pt_referral_generate"),
    path("pt/api/alerts/<int:alert_id>/send/",      views_pt_alarm.referral_send,         name="pt_referral_send"),
    path("pt/api/alerts/<int:alert_id>/followup/",  views_pt_alarm.referral_mark_followup, name="pt_referral_followup"),
    path("pt/api/alerts/<int:alert_id>/print/",     views_pt_alarm.referral_print,         name="pt_referral_print"),
    path("pt/api/alerts/<int:alert_id>/action/",    views_pt_alarm.alarm_action,           name="pt_alarm_action"),

    # ── Phase 7: Audit Loop ────────────────────────────────────────
    path("pt/api/sessions/<int:timeline_id>/soap-edit/",
                                             views_pt_alarm.save_soap_edit,          name="pt_soap_edit"),
    path("pt/api/alerts/<int:alert_id>/decision/",
                                             views_pt_alarm.save_alarm_decision,     name="pt_alarm_decision"),
    path("pt/api/patients/<str:patient_id>/doc/<str:doc_type>/edit/",
                                             views_pt_alarm.save_doc_edit,           name="pt_doc_edit"),
    path("pt/api/audit/export/",             views_pt_alarm.export_audit_pairs,      name="pt_audit_export"),

    # ── 이메일 발송 ────────────────────────────────────────────────────
    path("pt/api/patients/<str:patient_id>/contacts/",
                                             views_pt_alarm.patient_contacts,        name="pt_contacts"),
    path("pt/api/contacts/<int:contact_id>/delete/",
                                             views_pt_alarm.patient_contact_delete,  name="pt_contact_delete"),
    path("pt/api/docs/send-email/",          views_pt_alarm.send_document_email,     name="pt_doc_send_email"),

    # ── Pilot Feedback ─────────────────────────────────────────────────
    path("pt/api/feedback/",                 views_pt_alarm.submit_feedback,         name="pt_feedback"),

    # ── Interview Research ──────────────────────────────────────────────
    path("pt/api/interview/respond/",        views_pt_alarm.interview_respond,       name="pt_interview_respond"),

    # ── E-Fax ──────────────────────────────────────────────────────────
    path("pt/api/efax/",                     views_pt_alarm.efax_referral,           name="pt_efax"),

    path("pt/api/backfill-rescore/",            views_pt_alarm.backfill_rescore_ajax,  name="pt_backfill_rescore"),
    path("pt/api/admin/clear/",                 views_pt_alarm.admin_clear_sessions,   name="pt_admin_clear"),
    path("pt/api/admin/reseed/",                views_pt_alarm.admin_reseed_ajax,      name="pt_admin_reseed"),

    # ── Compliance Dashboard ──────────────────────────────────────────────
    path("pt/api/compliance/",                        views_pt_alarm.compliance_dashboard_json, name="pt_compliance"),
    path("pt/api/compliance/<str:patient_id>/",       views_pt_alarm.compliance_case_detail,    name="pt_compliance_case"),

    # ── 웹 UI ─────────────────────────────────────────────────────────────
    path("pt/",                views_pt_alarm.index,            name="pt_index"),
    path("pt/analyze/",        views_pt_alarm.analyze_view,     name="pt_analyze"),
    path("pt/result/",         views_pt_alarm.result_view,      name="pt_result"),
    path("pt/staff/events/",   views_pt_alarm.event_dashboard,  name="pt_event_dashboard"),

    # ── Landing page waitlist (no auth) ──────────────────────────────────
    path("api/pt/waitlist/", views_api.waitlist, name="waitlist"),
]
