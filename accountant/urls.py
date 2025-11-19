from django.urls import path
from . import views
from .views import *


urlpatterns = [
    path('activities', get_all_activities),
    path('incomes', income_list),
    path('expenses', expense_list),
    path('create-expenses', create_expense),
    path('financial-summary', financial_summary),
    path('non-superusers', non_superuser_list),
    path('users/<int:user_id>', user_profile_detail),
    path('update-user-role/<int:user_id>', update_user_role),
    path('roles', list_roles),
    path('appointments', list_appointments),
    path('statistics', statistics_summary),
    path('admission-discharge-stats', admission_discharge_statistics),
    path('bed-occupancy-details', bed_occupancy_details),
    path('create-ward', create_ward),
    path('wards', get_all_wards),
    path('create-room', create_room),
    path('create-drug', create_drug),
    path('update-drug/<int:drug_id>', update_drug),
]