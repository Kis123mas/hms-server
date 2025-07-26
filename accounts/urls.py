from django.urls import path
from .views import *
urlpatterns = [
    path('register', register_api),
    path('login', login_api),
    path('logout', logout_user),
]