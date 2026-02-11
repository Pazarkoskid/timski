from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import CustomUser, Child


class CustomUserCreationForm(UserCreationForm):
    class Meta:
        model = CustomUser
        fields = ('username', 'email', 'first_name', 'last_name', 'role', 'phone', 'date_of_birth')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # При регистрација, секогаш Parent
        self.fields['role'].initial = 'parent'
        self.fields['role'].widget = forms.HiddenInput()


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