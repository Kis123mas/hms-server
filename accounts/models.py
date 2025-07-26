from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager, Group
from django.utils import timezone


class CustomUserManager(BaseUserManager):
    def create_user(self, email, password=None, first_name=None, last_name=None, role=None):
        if not email:
            raise ValueError('Users must have an email address')
        email = self.normalize_email(email)
        user = self.model(email=email, first_name=first_name, last_name=last_name, role=role)
        user.set_password(password)
        user.save(using=self._db)
        
        # Lazy import to avoid circular dependency
        from healthManagement.models import Profile
        Profile.objects.create(user=user)
        
        return user

    def create_superuser(self, email, password, first_name=None, last_name=None, role=None):
        user = self.create_user(email, password, first_name, last_name, role)
        user.is_staff = True
        user.is_superuser = True
        user.save(using=self._db)
        return user

class CustomUser(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(unique=True, max_length=255)
    first_name = models.CharField(max_length=64, blank=True, null=True)
    last_name = models.CharField(max_length=64, blank=True, null=True)
    role = models.ForeignKey(Group, on_delete=models.SET_NULL, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)

    objects = CustomUserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']

    def __str__(self):
        return self.email



