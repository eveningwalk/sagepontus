from vertical_pt.models import RedFlagAlert
from django.contrib.auth.models import User
from vertical_pt.engine.referral import generate_referral_letter_ai

u = User.objects.get(username='chrisnam')
alert = RedFlagAlert.objects.filter(timeline__therapist=u).last()

if not alert:
    print("No alerts found")
else:
    print(f"Alert: id={alert.id}, condition={alert.condition}, alarm={alert.alarm_level}")
    result = generate_referral_letter_ai(
        alert,
        patient_id=alert.timeline.patient_id,
        therapist_name='Test PT',
    )
    print("\n--- RESULT (first 400 chars) ---")
    print(result[:400])
