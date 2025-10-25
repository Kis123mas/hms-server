from django.contrib import admin
from .models import *

# Register your models here.
admin.site.register(ActiveWebSocketConnection),
admin.site.register(VerificationCode),
admin.site.register(Profile),
admin.site.register(Department),
admin.site.register(Appointment),
admin.site.register(Notification),
admin.site.register(PatientEMR),
admin.site.register(PatientVital),
admin.site.register(TestResult),
admin.site.register(Drug),
admin.site.register(Prescription),
admin.site.register(Ward),
admin.site.register(Room),
admin.site.register(AllocateBed),
