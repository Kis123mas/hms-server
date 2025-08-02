from django.contrib import admin
from .models import *

# Register your models here.
admin.site.register(Profile),
admin.site.register(Appointment),
admin.site.register(PatientEMR),
admin.site.register(PatientVital),
admin.site.register(TestResult),
admin.site.register(Drug),