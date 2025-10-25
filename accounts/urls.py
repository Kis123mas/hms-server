from django.urls import path
from .views import *
urlpatterns = [
    path('register', register_api),
    path('login', login_api),
    path('logout', logout_user),
    path('regenerate-code', regenerate_code_api),
    path('verify-code', verify_code_api),
    path('forgot-password', forgot_password_api),
    path('reset-password', reset_password_api),
    path('change-password', change_password),
    path('google-login', google_login_api),
]