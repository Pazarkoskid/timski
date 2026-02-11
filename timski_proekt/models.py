from django.db import models
from django.contrib.auth.models import AbstractUser
import json


class CustomUser(AbstractUser):
    ROLE_CHOICES = (
        ('admin', 'Admin'),
        ('therapist', 'Therapist'),
        ('parent', 'Parent'),
    )

    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='parent')
    phone = models.CharField(max_length=20, blank=True, null=True)
    date_of_birth = models.DateField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"


class Child(models.Model):
    parent = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='children')
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    birth_date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

    def get_age_in_months(self):
        from datetime import date
        today = date.today()
        months = (today.year - self.birth_date.year) * 12 + (today.month - self.birth_date.month)
        return months


class Questionnaire(models.Model):
    months = models.IntegerField()
    title = models.CharField(max_length=200)
    age_range = models.CharField(max_length=100)
    json_file = models.CharField(max_length=200)

    def __str__(self):
        return f"{self.title} ({self.months} месеци)"


class ParentResponse(models.Model):
    parent = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='responses')
    child = models.ForeignKey(Child, on_delete=models.CASCADE, related_name='responses')
    questionnaire = models.ForeignKey(Questionnaire, on_delete=models.CASCADE)

    # Серијализирани податоци за одговорите
    answers_json = models.TextField()  # JSON одговори на прашањата
    notes = models.TextField(blank=True, null=True)

    # Поени од терапевтот
    therapist_points = models.TextField(blank=True, null=True)  # JSON со поени за секое прашање
    total_points = models.IntegerField(default=0)
    therapist_comments = models.TextField(blank=True, null=True)

    STATUS_CHOICES = (
        ('submitted', 'Поднесено'),
        ('reviewed', 'Одговорено'),
        ('completed', 'Завршено'),
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='submitted')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def get_answers(self):
        try:
            return json.loads(self.answers_json)
        except:
            return {}

    def get_therapist_points(self):
        try:
            return json.loads(self.therapist_points)
        except:
            return {}

    def __str__(self):
        return f"Одговор за {self.child} - {self.questionnaire}"