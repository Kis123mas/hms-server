from django.contrib import admin
from .models import *

# Register your models here.
admin.site.register(ActiveWebSocketConnection),
admin.site.register(VerificationCode),
admin.site.register(Profile),
admin.site.register(Department),
admin.site.register(Appointment),
admin.site.register(Notification),
admin.site.register(VitalSign),
