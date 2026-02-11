from django.contrib.auth.forms import AuthenticationForm
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import JsonResponse, HttpResponseForbidden
from django.db.models import Q
import json
from .models import CustomUser, Child, Questionnaire, ParentResponse
from .forms import CustomUserCreationForm, ChildForm, TherapistResponseForm


# Хелпер функции за проверка на роли
def is_admin(user):
    return user.is_authenticated and user.role == 'admin'


def is_therapist(user):
    return user.is_authenticated and user.role == 'therapist'


def is_parent(user):
    return user.is_authenticated and user.role == 'parent'


# Главна страна
def index(request):
    # prasalnici = [2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 22, 27, 33, 42, 48, 54, 60]
    return render(request, "index.html")

# Прикажи прашалник
@login_required
def prasalnici(request, mesec):
    # Провери дали прашалникот постои во базата
    questionnaire = get_object_or_404(Questionnaire, months=mesec)

    with open(f"timski_proekt/Prasalnici/{mesec}meseci.json", encoding="utf-8") as f:
        quiz = json.load(f)

    if request.method == "GET":
        return render(request, "prasalnici.html", {"quiz": quiz, "mesec": mesec})

    # POST - зачувување на одговори
    elif request.method == "POST" and is_parent(request.user):
        # Земи го детето (во овој пример, го земаме првото дете)
        child = request.user.children.first()
        if not child:
            return redirect('add_child')

        # Собирање на одговорите
        answers = {}
        for key, value in request.POST.items():
            if key != 'csrfmiddlewaretoken' and not key.endswith('_command') and not key.startswith('txt_'):
                answers[key] = value
            elif key.endswith('_command'):
                # Зачувување на команди
                q_id = key.replace('_command', '')
                if q_id not in answers:
                    answers[q_id] = {}
                answers[q_id]['commands'] = request.POST.getlist(key)
            elif key.startswith('txt_'):
                # Текст одговори
                q_id = key.replace('txt_', '')
                if q_id not in answers:
                    answers[q_id] = {}
                answers[q_id]['text'] = value

        # Создај ParentResponse
        response = ParentResponse.objects.create(
            parent=request.user,
            child=child,
            questionnaire=questionnaire,
            answers_json=json.dumps(answers),
            notes=request.POST.get('notes', ''),
            status='submitted'
        )

        return redirect('parent_dashboard')


# Регистрација (секогаш Parent)
def register(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.role = 'parent'  # Секогаш parent при регистрација
            user.save()
            login(request, user)
            return redirect('add_child')  # Пренасочи кон додавање дете после регистрација
        else:
            # Прикажи грешки
            return render(request, 'registration/register.html', {'form': form})
    else:
        form = CustomUserCreationForm()
    return render(request, 'registration/register.html', {'form': form})
# Логин
def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)

            # Пренасочување според улогата
            if user.role == 'admin':
                return redirect('admin_dashboard')
            elif user.role == 'therapist':
                return redirect('therapist_dashboard')
            else:
                return redirect('parent_dashboard')
        else:
            return render(request, 'registration/login.html', {'form': form})
    else:
        form = AuthenticationForm()

    # Зачувај ја next страницата ако постои
    next_page = request.GET.get('next', '')
    return render(request, 'registration/login.html', {'form': form, 'next': next_page})


# Logout
def logout_view(request):
    logout(request)
    return redirect('index')


# Parent Dashboard
@login_required
@user_passes_test(is_parent)
def parent_dashboard(request):
    responses = ParentResponse.objects.filter(parent=request.user).order_by('-created_at')
    children = request.user.children.all()
    return render(request, 'parent_dashboard.html', {
        'responses': responses,
        'children': children
    })


# Додади дете
@login_required
@user_passes_test(is_parent)
def add_child(request):
    if request.method == 'POST':
        form = ChildForm(request.POST)
        if form.is_valid():
            child = form.save(commit=False)
            child.parent = request.user
            child.save()
            return redirect('parent_dashboard')
    else:
        form = ChildForm()
    return render(request, 'add_child.html', {'form': form})


# Therapist Dashboard
@login_required
@user_passes_test(is_therapist)
def therapist_dashboard(request):
    # Прикажи ги сите одговори што чекаат на преглед
    responses = ParentResponse.objects.filter(status='submitted').order_by('-created_at')
    reviewed = ParentResponse.objects.filter(status='reviewed').order_by('-updated_at')
    return render(request, 'therapist_dashboard.html', {
        'pending_responses': responses,
        'reviewed_responses': reviewed
    })


# Therapist Response View
@login_required
@user_passes_test(is_therapist)
def therapist_response(request, response_id):
    parent_response = get_object_or_404(ParentResponse, id=response_id)

    if request.method == 'POST':
        # Обработка на поените
        points_data = {}
        total_points = 0

        for key, value in request.POST.items():
            if key.startswith('points_'):
                q_id = key.replace('points_', '')
                if value:
                    points = int(value)
                    points_data[q_id] = points
                    total_points += points

        # Зачувување на поените
        parent_response.therapist_points = json.dumps(points_data)
        parent_response.total_points = total_points
        parent_response.therapist_comments = request.POST.get('comments', '')
        parent_response.status = 'reviewed'
        parent_response.save()

        return redirect('therapist_dashboard')

    # GET - прикажи ја формата
    # Вчитај го прашалникот
    with open(f"timski_proekt/Prasalnici/{parent_response.questionnaire.months}meseci.json", encoding="utf-8") as f:
        quiz = json.load(f)

    # Вчитај ги одговорите од родителот
    answers = parent_response.get_answers()

    # Парсирај ги одговорите за полесен пристап во template
    parsed_answers = {}
    for key, value in answers.items():
        if isinstance(value, dict):
            # Ако имаме dict (може да е речник со команди и примероци)
            parsed_answers[key] = value
        else:
            # Ако е обичен стринг
            parsed_answers[key] = value

    therapist_points = parent_response.get_therapist_points()

    return render(request, 'therapist_response.html', {
        'response': parent_response,
        'quiz': quiz,
        'answers': parsed_answers,
        'therapist_points': therapist_points,
    })


# Admin Dashboard
@login_required
@user_passes_test(is_admin)
def admin_dashboard(request):
    users = CustomUser.objects.all()
    responses = ParentResponse.objects.all().order_by('-created_at')
    return render(request, 'admin_dashboard.html', {
        'users': users,
        'responses': responses
    })


# Детали за Parent Response
@login_required
def response_detail(request, response_id):
    response = get_object_or_404(ParentResponse, id=response_id)

    # Проверка на пристап
    if not (request.user == response.parent or
            request.user.role == 'therapist' or
            request.user.role == 'admin'):
        return HttpResponseForbidden("Немате пристап до овој одговор")

    with open(f"timski_proekt/Prasalnici/{response.questionnaire.months}meseci.json", encoding="utf-8") as f:
        quiz = json.load(f)

    answers = response.get_answers()
    therapist_points = response.get_therapist_points()

    return render(request, 'response_detail.html', {
        'response': response,
        'quiz': quiz,
        'answers': answers,
        'therapist_points': therapist_points
    })