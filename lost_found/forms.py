from django import forms
from django.core.exceptions import ValidationError
from .models import ItemReport, ItemImage


class ItemReportForm(forms.ModelForm):
    images = forms.FileField(required=False, widget=forms.ClearableFileInput())

    class Meta:
        model = ItemReport
        exclude = ('user', 'status', 'reviewed_by', 'review_remarks')
        widgets = {
            'date_occurrence': forms.DateInput(attrs={'type': 'date'}),
            'approximate_time': forms.TimeInput(attrs={'type': 'time'}),
            'description': forms.Textarea(attrs={'rows': 4}),
            'identifying_details': forms.Textarea(attrs={'rows': 3}),
        }

    def clean_images(self):
        image = self.cleaned_data.get('images')
        if image and image.size > 5 * 1024 * 1024:
            raise ValidationError('Each image must be 5 MB or smaller.')
        return image
