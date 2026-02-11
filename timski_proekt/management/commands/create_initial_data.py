from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from timski_proekt.models import Questionnaire
import json
import os


class Command(BaseCommand):
    help = 'Создај почетни податоци за апликацијата'

    def handle(self, *args, **kwargs):
        User = get_user_model()

        # Создади администратор
        if not User.objects.filter(username='admin').exists():
            admin = User.objects.create_superuser(
                username='admin',
                email='admin@example.com',
                password='admin123',
                role='admin'
            )
            self.stdout.write(self.style.SUCCESS('Администратор креиран'))

        # Создади терапевт
        if not User.objects.filter(username='therapist').exists():
            therapist = User.objects.create_user(
                username='therapist',
                email='therapist@example.com',
                password='therapist123',
                role='therapist',
                first_name='Терапевт',
                last_name='Пример'
            )
            self.stdout.write(self.style.SUCCESS('Терапевт креиран'))

        # Вчитај ги прашалниците од JSON датотеките
        prasalnici = [2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 22, 27, 33, 42, 48, 54, 60]

        for mesec in prasalnici:
            json_file = f"timski_proekt/Prasalnici/{mesec}meseci.json"
            if os.path.exists(json_file):
                with open(json_file, encoding='utf-8') as f:
                    data = json.load(f)

                if not Questionnaire.objects.filter(months=mesec).exists():
                    Questionnaire.objects.create(
                        months=mesec,
                        title=data.get('title', f'Прашалник за {mesec} месеци'),
                        age_range=data.get('age_range', ''),
                        json_file=json_file
                    )
                    self.stdout.write(self.style.SUCCESS(f'Прашалник за {mesec} месеци креиран'))