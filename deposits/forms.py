from django import forms
from .models import FDR


class DateInput(forms.DateInput):
    input_type = "date"


class FDRForm(forms.ModelForm):
    class Meta:
        model = FDR
        fields = ["institution", "fdr_number", "bank_name", "amount",
                  "issue_date", "maturity_date", "document"]
        widgets = {
            "issue_date": DateInput(format="%Y-%m-%d"),
            "maturity_date": DateInput(format="%Y-%m-%d"),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user is not None and not user.is_staff:
            del self.fields["institution"]

    def clean(self):
        data = super().clean()
        issue, mat = data.get("issue_date"), data.get("maturity_date")
        if issue and mat and mat <= issue:
            self.add_error("maturity_date", "Maturity date must be after issue date.")
        return data