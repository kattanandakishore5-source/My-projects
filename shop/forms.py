from django import forms
from .models import ProductReview


class ReviewForm(forms.ModelForm):
    class Meta:
        model = ProductReview
        fields = ['rating', 'review_text', 'image']
        widgets = {
            'rating': forms.HiddenInput(attrs={'id': 'id_rating'}),
            'review_text': forms.Textarea(attrs={'class': 'form-control store-input', 'rows': 3, 'placeholder': 'Write your review here...'}),
            'image': forms.FileInput(attrs={'class': 'form-control-file text-secondary'}),
        }

    def clean_image(self):
        image = self.cleaned_data.get('image')
        if image:
            if image.size > 5 * 1024 * 1024:
                raise forms.ValidationError("Image file size must be less than 5MB.")
        return image