from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("vertical_pt", "0012_add_waitlist_entry"),
    ]

    operations = [
        migrations.AddField(
            model_name="redflagalert",
            name="monitoring_flagged",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="redflagalert",
            name="monitoring_flagged_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
