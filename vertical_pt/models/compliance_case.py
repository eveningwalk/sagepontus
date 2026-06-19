import datetime
from django.db import models
from django.contrib.auth.models import User

# Days from treatment start within which physician must be notified, by US state.
# None = unrestricted direct access (no deadline).
DIRECT_ACCESS_DEADLINES = {
    # Unrestricted
    "AK": None, "AZ": None, "CA": None, "CO": None, "CT": None,
    "DC": None, "FL": None, "GA": None, "HI": None, "ID": None,
    "IL": None, "IN": None, "IA": None, "KS": None, "KY": None,
    "LA": None, "ME": None, "MD": None, "MA": None, "MI": None,
    "MN": None, "MT": None, "NE": None, "NV": None, "NH": None,
    "NM": None, "NC": None, "ND": None, "OH": None, "OK": None,
    "OR": None, "PA": None, "RI": None, "SC": None, "SD": None,
    "TN": None, "TX": None, "UT": None, "VT": None, "VA": None,
    "WA": None, "WV": None, "WI": None, "WY": None,
    # Restricted
    "AL": 30, "AR": 30, "DE": 30, "MS": 30, "MO": 30, "NJ": 30,
    "NY": 30, "NJ": 30, "NY": 10, "NJ": 30,
}

# Default insurance filing deadlines (days from service date)
INSURER_FILING_DAYS = {
    "medicare":          365,
    "medicaid":          365,
    "aetna":             180,
    "cigna":             180,
    "united":            180,
    "bcbs":              180,
    "humana":            180,
    "tricare":           365,
    "workers_comp":      365,
    "other_commercial":  90,
    "self_pay":          None,
}

# Default appeal deadlines (days from rejection date)
INSURER_APPEAL_DAYS = {
    "medicare":          120,
    "medicaid":          90,
    "aetna":             180,
    "cigna":             60,
    "united":            60,
    "bcbs":              180,
    "humana":            60,
    "tricare":           90,
    "workers_comp":      60,
    "other_commercial":  60,
    "self_pay":          None,
}


class ComplianceCase(models.Model):
    INSURER_CHOICES = [
        ("medicare",         "Medicare"),
        ("medicaid",         "Medicaid"),
        ("aetna",            "Aetna"),
        ("cigna",            "Cigna"),
        ("united",           "United Healthcare"),
        ("bcbs",             "BCBS"),
        ("humana",           "Humana"),
        ("tricare",          "TRICARE"),
        ("workers_comp",     "Workers' Comp"),
        ("other_commercial", "Other Commercial"),
        ("self_pay",         "Self Pay"),
    ]

    therapist  = models.ForeignKey(User, on_delete=models.CASCADE, related_name="compliance_cases")
    patient_id = models.CharField(max_length=100, db_index=True)

    # ── Direct Access ─────────────────────────────────────────────────────────
    treatment_start_date  = models.DateField(null=True, blank=True)
    state                 = models.CharField(max_length=2, blank=True)
    da_deadline_days      = models.IntegerField(null=True, blank=True)  # None = unrestricted
    physician_notified_at = models.DateField(null=True, blank=True)
    plan_of_care_sent_at  = models.DateField(null=True, blank=True)

    # ── Insurance ─────────────────────────────────────────────────────────────
    insurer_type         = models.CharField(max_length=30, choices=INSURER_CHOICES, blank=True)
    insurer_name         = models.CharField(max_length=100, blank=True)
    claim_submitted_at   = models.DateField(null=True, blank=True)
    claim_rejected_at    = models.DateField(null=True, blank=True)
    appeal_submitted_at  = models.DateField(null=True, blank=True)
    appeal_deadline_days = models.IntegerField(null=True, blank=True)  # override default

    notes      = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [("therapist", "patient_id")]
        ordering = ["-updated_at"]

    def __str__(self):
        return f"Compliance/{self.patient_id} ({self.therapist.username})"

    # ── Computed deadline helpers ─────────────────────────────────────────────

    def da_physician_deadline(self) -> datetime.date | None:
        """Date by which physician must be notified under Direct Access rules."""
        if not self.treatment_start_date:
            return None
        days = self.da_deadline_days
        if days is None:
            # Pull from state lookup if state is set
            if self.state:
                days = DIRECT_ACCESS_DEADLINES.get(self.state.upper())
            if days is None:
                return None
        return self.treatment_start_date + datetime.timedelta(days=days)

    def insurance_filing_deadline(self) -> datetime.date | None:
        """Last date to submit insurance claim."""
        if not self.treatment_start_date or not self.insurer_type:
            return None
        days = INSURER_FILING_DAYS.get(self.insurer_type)
        if days is None:
            return None
        return self.treatment_start_date + datetime.timedelta(days=days)

    def appeal_deadline(self) -> datetime.date | None:
        """Last date to file appeal after claim rejection."""
        if not self.claim_rejected_at or not self.insurer_type:
            return None
        days = self.appeal_deadline_days or INSURER_APPEAL_DAYS.get(self.insurer_type)
        if days is None:
            return None
        return self.claim_rejected_at + datetime.timedelta(days=days)

    def days_until(self, deadline: datetime.date | None) -> int | None:
        """Positive = days remaining, 0 = today, negative = overdue."""
        if deadline is None:
            return None
        return (deadline - datetime.date.today()).days

    def to_dict(self) -> dict:
        today = datetime.date.today()

        da_deadline       = self.da_physician_deadline()
        filing_deadline   = self.insurance_filing_deadline()
        appeal_dl         = self.appeal_deadline()

        def _status(deadline, completed_at):
            if completed_at:
                return "done"
            if deadline is None:
                return "n/a"
            days = (deadline - today).days
            if days < 0:
                return "overdue"
            if days <= 3:
                return "urgent"
            return "ok"

        return {
            "patient_id":             self.patient_id,
            # Direct Access
            "treatment_start_date":   str(self.treatment_start_date) if self.treatment_start_date else None,
            "state":                  self.state,
            "da_deadline_days":       self.da_deadline_days,
            "da_deadline_date":       str(da_deadline) if da_deadline else None,
            "da_days_left":           self.days_until(da_deadline),
            "physician_notified_at":  str(self.physician_notified_at) if self.physician_notified_at else None,
            "plan_of_care_sent_at":   str(self.plan_of_care_sent_at) if self.plan_of_care_sent_at else None,
            "da_status":              _status(da_deadline, self.physician_notified_at),
            "poc_status":             _status(da_deadline, self.plan_of_care_sent_at),
            # Insurance
            "insurer_type":           self.insurer_type,
            "insurer_name":           self.insurer_name,
            "filing_deadline_date":   str(filing_deadline) if filing_deadline else None,
            "filing_days_left":       self.days_until(filing_deadline),
            "claim_submitted_at":     str(self.claim_submitted_at) if self.claim_submitted_at else None,
            "claim_rejected_at":      str(self.claim_rejected_at) if self.claim_rejected_at else None,
            "appeal_deadline_date":   str(appeal_dl) if appeal_dl else None,
            "appeal_days_left":       self.days_until(appeal_dl),
            "appeal_submitted_at":    str(self.appeal_submitted_at) if self.appeal_submitted_at else None,
            "filing_status":          _status(filing_deadline, self.claim_submitted_at),
            "appeal_status":          _status(appeal_dl, self.appeal_submitted_at) if self.claim_rejected_at else "n/a",
            # Meta
            "notes":                  self.notes,
            "updated_at":             self.updated_at.strftime("%Y-%m-%d %H:%M"),
        }
