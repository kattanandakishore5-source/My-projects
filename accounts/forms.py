from django.contrib.auth.forms import UserCreationForm
from .models import CustomUser

class CustomUserCreationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = CustomUser
        # Optimized: Dynamically appends to existing default fields to prevent losing base validation logic
        fields = UserCreationForm.Meta.fields + ('email', 'phone_number', 'address')