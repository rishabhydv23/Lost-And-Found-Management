from django import forms
from django.core.exceptions import ValidationError
from .models import ItemReport, ItemImage


class ItemReportForm(forms.ModelForm):
    images = forms.FileField(required=False, widget=forms.ClearableFileInput())

    class Meta:
        model = ItemReport
        exclude = ('user', 'status', 'reviewed_by', 'review_remarks')
        widgets = {
            'item_name': forms.TextInput(attrs={'placeholder': 'e.g. Black backpack'}),
            'description': forms.Textarea(attrs={'rows': 4, 'placeholder': "Size, condition, what's inside, anything visible at a glance"}),
            'color': forms.TextInput(attrs={'placeholder': 'e.g. Navy blue'}),
            'brand': forms.TextInput(attrs={'placeholder': 'e.g. Wildcraft'}),
            'identifying_details': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Name tags, stickers, scratches, serial numbers. Keep one detail private so you can verify the real owner.'}),
            'custody': forms.TextInput(attrs={'placeholder': 'e.g. Security desk, Block 32 or kept with me'}),
            'date_occurrence': forms.DateInput(attrs={'type': 'date'}),
            'approximate_time': forms.TimeInput(attrs={'type': 'time'}),
        }

    def clean_images(self):
        image = self.cleaned_data.get('images')
        if image and image.size > 5 * 1024 * 1024:
            raise ValidationError('Each image must be 5 MB or smaller.')
        return image
