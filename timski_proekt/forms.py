from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import CustomUser, Child


class CustomUserCreationForm(UserCreationForm):
    email = forms.EmailField(required=True)
    first_name = forms.CharField(max_length=30, required=False)
    last_name = forms.CharField(max_length=30, required=False)
    phone = forms.CharField(max_length=20, required=False)

    class Meta:
        model = CustomUser
        fields = ('username', 'email', 'first_name', 'last_name', 'role', 'phone', 'date_of_birth')
        widgets = {
            'date_of_birth': forms.DateInput(attrs={'type': 'date'}),
        }
    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data.get('first_name', '')
        user.last_name = self.cleaned_data.get('last_name', '')
        user.phone = self.cleaned_data.get('phone', '')
        if commit:
            user.save()
        return user


class ChildForm(forms.ModelForm):
    class Meta:
        model = Child
        fields = ('first_name', 'last_name', 'birth_date')
        widgets = {
            'birth_date': forms.DateInput(attrs={'type': 'date'}),
        }


class TherapistResponseForm(forms.Form):
    def __init__(self, *args, **kwargs):
        questions = kwargs.pop('questions', [])
        super().__init__(*args, **kwargs)

        for section in questions:
            for q in section.get('questions', []):
                field_name = f"points_{q['id']}"
                self.fields[field_name] = forms.IntegerField(
                    label=f"Поени за: {q['text'][:50]}...",
                    min_value=0,
                    max_value=10,
                    required=False,
                    widget=forms.NumberInput(attrs={'class': 'form-control'})
                )

    comments = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
        required=False,
        label="Коментари"
    )