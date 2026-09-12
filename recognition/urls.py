from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

app_name = "recognition"

urlpatterns = [
    # Page views
    path('', views.index, name='recognize'),
    path('history/', views.history, name='history'),
    path('explore/', views.explore, name='explore'),
    path('modelinfo/', views.modelinfo, name='modelinfo'),
    path('settings/', views.settings, name='settings'),

    # Authentication
    path('login/', views.login_page, name='login'),
    path('register/', views.register_page, name='register'),
    path('account/', views.account, name='account'),
    path('logout/', views.logout_page, name='logout'),

    # API endpoints (keep existing)
    path('api/predict/', views.predict, name='predict'),
    path('api/signup/', views.api_signup, name='signup'),
    path('api/login/', views.api_login, name='api_login'),
    path('api/logout/', views.api_logout, name='api_logout'),
    path('api/me/', views.api_me, name='me'),
    path('api/history/', views.api_history, name='api_history'),
    path('api/settings/', views.api_settings, name='api_settings'),
]
