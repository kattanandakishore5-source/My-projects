from django import forms
from .models import ProductReview




class CouponApplyForm(forms.Form):
    code = forms.CharField()


class ReviewForm(forms.ModelForm):
    class Meta:
        model = ProductReview
        fields = ['rating', 'review_text', 'image']
        widgets = {
            'rating': forms.NumberInput(attrs={'class': 'form-control store-input', 'min': 1, 'max': 5}),
            'review_text': forms.Textarea(attrs={'class': 'form-control store-input', 'rows': 3, 'placeholder': 'Write your review here...'}),
            'image': forms.FileInput(attrs={'class': 'form-control-file text-secondary'}),
        }