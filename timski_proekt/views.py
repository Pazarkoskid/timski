from django.contrib import messages
from django.contrib.auth.forms import AuthenticationForm
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required, user_passes_test

from django.http import HttpResponseForbidden, HttpResponse
from django.http import JsonResponse, HttpResponseForbidden, HttpResponse
from django.db.models import Q, Avg, Count
import json
import pdfkit
from django.template.loader import render_to_string

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
    return render(request, "index.html")

# Прикажи прашалник
@login_required
def prasalnici(request, mesec):
    questionnaire = get_object_or_404(Questionnaire, months=mesec)

    with open(f"timski_proekt/Prasalnici/{mesec}meseci.json", encoding="utf-8") as f:
        quiz = json.load(f)

    if request.method == "GET":
        return render(request, "prasalnici.html", {"quiz": quiz, "mesec": mesec})

    elif request.method == "POST" and is_parent(request.user):
        child = request.user.children.first()
        if not child:
            return redirect('add_child')

        answers = {}
        for key, value in request.POST.items():
            if key == "csrfmiddlewaretoken":
                continue
            if key.startswith("txt_"):
                q_id = key.replace("txt_", "")
                if q_id not in answers:
                    answers[q_id] = {}
                answers[q_id]["text"] = value
            elif not key.endswith("_command"):
                q_id = key
                if q_id not in answers:
                    answers[q_id] = {}
                answers[q_id]["answer"] = value
            elif key.endswith("_command"):
                q_id = key.replace("_command", "")
                if q_id not in answers:
                    answers[q_id] = {}
                answers[q_id]["commands"] = request.POST.getlist(key)

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
            user.role = 'parent'
            user.save()
            login(request, user)
            return redirect('add_child')
        else:
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

    next_page = request.GET.get('next', '')
    return render(request, 'registration/login.html', {'form': form, 'next': next_page})


# Logout
def logout_view(request):
    logout(request)
    return redirect('index')


# ─── 1. Parent Dashboard ──────────────────────────────────────────────────────
@login_required
@user_passes_test(is_parent)
def parent_dashboard(request):
    responses = ParentResponse.objects.filter(parent=request.user).order_by('-created_at')
    children = request.user.children.all()

    # Број на одговори кои чекаат на преглед
    pending_count = responses.filter(status='submitted').count()

    # Просечни поени (само прегледани одговори со поени > 0)
    avg_result = responses.filter(
        status__in=['reviewed', 'completed'],
        total_points__gt=0
    ).aggregate(avg=Avg('total_points'))
    average_points = round(avg_result['avg']) if avg_result['avg'] else None

    return render(request, 'parent_dashboard.html', {
        'responses': responses,
        'children': children,
        'pending_count': pending_count,       # ← Чекаат на преглед
        'average_points': average_points,     # ← Просечни поени
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


# ─── 2. Therapist Dashboard ───────────────────────────────────────────────────
@login_required
@user_passes_test(is_therapist)
def therapist_dashboard(request):
    pending_responses = ParentResponse.objects.filter(status='submitted').order_by('-created_at')
    reviewed_responses = ParentResponse.objects.filter(
        status__in=['reviewed', 'completed']
    ).order_by('-updated_at')

    # Пребарување — активира се кога има query параметри
    # search_params е секогаш речник — празен кога нема пребарување
    search_params = {
        'child': '', 'parent': '', 'age_from': '', 'age_to': '',
        'questionnaire': '', 'questionnaire_int': None,
        'date_from': '', 'date_to': '', 'status': '',
    }
    if request.GET.get('tab') == 'search':
        qs = ParentResponse.objects.all().order_by('-created_at')

        child_name = request.GET.get('child', '').strip()
        parent_name = request.GET.get('parent', '').strip()
        age_from = request.GET.get('age_from', '')
        age_to = request.GET.get('age_to', '')
        questionnaire = request.GET.get('questionnaire', '')
        date_from = request.GET.get('date_from', '')
        date_to = request.GET.get('date_to', '')
        status = request.GET.get('status', '')

        if child_name:
            qs = qs.filter(
                Q(child__first_name__icontains=child_name) |
                Q(child__last_name__icontains=child_name)
            )
        if parent_name:
            qs = qs.filter(
                Q(parent__first_name__icontains=parent_name) |
                Q(parent__last_name__icontains=parent_name) |
                Q(parent__username__icontains=parent_name)
            )
        if questionnaire:
            qs = qs.filter(questionnaire__months=questionnaire)
        if date_from:
            qs = qs.filter(created_at__date__gte=date_from)
        if date_to:
            qs = qs.filter(created_at__date__lte=date_to)
        if status:
            qs = qs.filter(status=status)

        # Филтер по возраст (во месеци) — пресметува во Python бидејќи е property
        if age_from or age_to:
            filtered_ids = []
            for r in qs:
                age = r.child.get_age_in_months()
                if age_from and age < int(age_from):
                    continue
                if age_to and age > int(age_to):
                    continue
                filtered_ids.append(r.id)
            qs = qs.filter(id__in=filtered_ids)

        search_params = {
            'child': child_name,
            'parent': parent_name,
            'age_from': age_from,
            'age_to': age_to,
            'questionnaire': questionnaire,
            'questionnaire_int': int(questionnaire) if questionnaire else None,
            'date_from': date_from,
            'date_to': date_to,
            'status': status,
        }
        search_results = qs
    else:
        search_results = None

    # Статистики за картичките
    unique_children_count = ParentResponse.objects.values('child').distinct().count()
    total_responses = ParentResponse.objects.count()
    age_months = Questionnaire.objects.values_list('months', flat=True).order_by('months')

    return render(request, 'therapist_dashboard.html', {
        'pending_responses': pending_responses,
        'reviewed_responses': reviewed_responses,
        'unique_children_count': unique_children_count,
        'total_responses': total_responses,
        'age_months': age_months,
        'search_results': search_results,     # ← Резултати од пребарување
        'search_params': search_params,        # ← За да останат вредностите во полињата
    })


# Therapist Response View
@login_required
@user_passes_test(is_therapist)
def therapist_response(request, response_id):
    parent_response = get_object_or_404(ParentResponse, id=response_id)

    if request.method == 'POST':
        points_data = {}
        total_points = 0

        for key, value in request.POST.items():
            if key.startswith('points_'):
                q_id = key.replace('points_', '')
                if value:
                    points = int(value)
                    points_data[q_id] = points
                    total_points += points

        parent_response.therapist_points = json.dumps(points_data)
        parent_response.total_points = total_points
        parent_response.therapist_comments = request.POST.get('comments', '')
        parent_response.status = 'reviewed'
        parent_response.save()

        return redirect('therapist_dashboard')

    with open(f"timski_proekt/Prasalnici/{parent_response.questionnaire.months}meseci.json", encoding="utf-8") as f:
        quiz = json.load(f)

    answers = parent_response.get_answers()
    parsed_answers = {}
    for key, value in answers.items():
        parsed_answers[key] = value if isinstance(value, dict) else value

    therapist_points = parent_response.get_therapist_points()

    return render(request, 'therapist_response.html', {
        'response': parent_response,
        'quiz': quiz,
        'answers': parsed_answers,
        'therapist_points': therapist_points,
    })


# ─── 3. Admin Dashboard ───────────────────────────────────────────────────────
@login_required
@user_passes_test(is_admin)
def admin_dashboard(request):
    users = CustomUser.objects.all()
    responses = ParentResponse.objects.all().order_by('-created_at')

    parent_count = CustomUser.objects.filter(role='parent').count()
    therapist_count = CustomUser.objects.filter(role='therapist').count()
    total_children = Child.objects.count()

    # Просечна возраст на децата
    avg_child_age = 0
    children = Child.objects.all()
    if children.exists():
        total_months = sum(child.get_age_in_months() for child in children)
        avg_child_age = round(total_months / children.count())

    # Најчест прашалник
    most_common_quiz_obj = (
        ParentResponse.objects
        .values('questionnaire__title')
        .annotate(cnt=Count('id'))
        .order_by('-cnt')
        .first()
    )
    most_common_quiz = most_common_quiz_obj['questionnaire__title'] if most_common_quiz_obj else '-'

    # Најактивен родител
    most_active_parent_obj = (
        ParentResponse.objects
        .values('parent__username', 'parent__first_name', 'parent__last_name')
        .annotate(cnt=Count('id'))
        .order_by('-cnt')
        .first()
    )
    if most_active_parent_obj:
        fn = most_active_parent_obj['parent__first_name']
        ln = most_active_parent_obj['parent__last_name']
        most_active_parent = f"{fn} {ln}".strip() or most_active_parent_obj['parent__username']
    else:
        most_active_parent = '-'

    # DELETE корисник
    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'delete_user':
            user_id = request.POST.get('user_id')
            try:
                user_to_delete = CustomUser.objects.get(id=user_id)
                if user_to_delete != request.user:          # не може да се избрише самиот себе
                    username = user_to_delete.username
                    user_to_delete.delete()
                    messages.success(request, f'Корисникот „{username}" е успешно избришан.')
                else:
                    messages.error(request, 'Не можете да го избришете вашиот сопствен профил.')
            except CustomUser.DoesNotExist:
                messages.error(request, 'Корисникот не постои.')
            return redirect('admin_dashboard')

        # Додади нов корисник
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.role = request.POST.get('role', 'parent')
            phone = request.POST.get('phone', '')
            if phone:
                user.phone = phone
            user.save()
            messages.success(request, f'Корисникот „{user.username}" е успешно креиран!')
            return redirect('admin_dashboard')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
    else:
        form = CustomUserCreationForm()

    context = {
        'users': users,
        'responses': responses,
        'parent_count': parent_count,
        'therapist_count': therapist_count,
        'total_children': total_children,
        'avg_child_age': avg_child_age,
        'most_common_quiz': most_common_quiz,       # ← Ново
        'most_active_parent': most_active_parent,   # ← Ново
        'form': form,
    }
    return render(request, 'admin_dashboard.html', context)


# Детали за Parent Response
@login_required
def response_detail(request, response_id):
    response = get_object_or_404(ParentResponse, id=response_id)

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


@login_required
def export_response_pdf(request, response_id):
    response = get_object_or_404(ParentResponse, id=response_id)

    if not (request.user == response.parent or
            request.user.role == 'therapist' or
            request.user.role == 'admin'):
        return HttpResponseForbidden("Немате пристап до овој одговор")

    with open(f"timski_proekt/Prasalnici/{response.questionnaire.months}meseci.json", encoding="utf-8") as f:
        quiz = json.load(f)

    answers = response.get_answers()
    therapist_points = response.get_therapist_points()

    html_string = render_to_string('pdf_export.html', {
        'response': response,
        'quiz': quiz,
        'answers': answers,
        'therapist_points': therapist_points,
        'user': request.user,
    })

    try:
        config = pdfkit.configuration(wkhtmltopdf=r'C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe')
        options = {
            'page-size': 'A4',
            'encoding': 'UTF-8',
            'enable-local-file-access': None,
            'margin-top': '20mm',
            'margin-right': '15mm',
            'margin-bottom': '20mm',
            'margin-left': '15mm',
        }
        pdf = pdfkit.from_string(html_string, False, configuration=config, options=options)
    except Exception as e:
        try:
            pdf = pdfkit.from_string(html_string, False, options=options)
        except:
            return HttpResponse(f"Грешка при генерирање PDF: {str(e)}", status=500)

    response_pdf = HttpResponse(pdf, content_type='application/pdf')
    filename = f"odgovor_{response.child.first_name}_{response.child.last_name}_{response.questionnaire.months}_meseci.pdf"
    response_pdf['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response_pdf
