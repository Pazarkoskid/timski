from django.contrib import admin
from django.urls import path
from django.contrib.auth import views as auth_views
from timski_proekt import views

urlpatterns = [
    # path('admin/', admin.site.urls),
    path('', views.index, name='index'),
    path('prasalnici/<int:mesec>/', views.prasalnici, name='prasalnici'),
    
    # Аутентификација
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('register/', views.register, name='register'),
    
    # Parent
    path('parent/dashboard/', views.parent_dashboard, name='parent_dashboard'),
    path('parent/add-child/', views.add_child, name='add_child'),
    
    # Therapist
    path('therapist/dashboard/', views.therapist_dashboard, name='therapist_dashboard'),
    path('therapist/response/<int:response_id>/', views.therapist_response, name='therapist_response'),
    
    # Admin
    path('admin/dashboard/', views.admin_dashboard, name='admin_dashboard'),
    
    # Заеднички
    path('response/<int:response_id>/', views.response_detail, name='response_detail'),
]