import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('vertical_pt', '0010_add_pilot_feedback'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='ComplianceCase',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('patient_id', models.CharField(db_index=True, max_length=100)),
                ('treatment_start_date', models.DateField(blank=True, null=True)),
                ('state', models.CharField(blank=True, max_length=2)),
                ('da_deadline_days', models.IntegerField(blank=True, null=True)),
                ('physician_notified_at', models.DateField(blank=True, null=True)),
                ('plan_of_care_sent_at', models.DateField(blank=True, null=True)),
                ('insurer_type', models.CharField(blank=True, choices=[
                    ('medicare', 'Medicare'), ('medicaid', 'Medicaid'),
                    ('aetna', 'Aetna'), ('cigna', 'Cigna'),
                    ('united', 'United Healthcare'), ('bcbs', 'BCBS'),
                    ('humana', 'Humana'), ('tricare', 'TRICARE'),
                    ('workers_comp', "Workers' Comp"),
                    ('other_commercial', 'Other Commercial'), ('self_pay', 'Self Pay'),
                ], max_length=30)),
                ('insurer_name', models.CharField(blank=True, max_length=100)),
                ('claim_submitted_at', models.DateField(blank=True, null=True)),
                ('claim_rejected_at', models.DateField(blank=True, null=True)),
                ('appeal_submitted_at', models.DateField(blank=True, null=True)),
                ('appeal_deadline_days', models.IntegerField(blank=True, null=True)),
                ('notes', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('therapist', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='compliance_cases',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                'ordering': ['-updated_at'],
                'unique_together': {('therapist', 'patient_id')},
            },
        ),
    ]
