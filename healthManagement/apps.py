from django.apps import AppConfig


class HealthmanagementConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'healthManagement'

    def ready(self):
        import healthManagement.signals