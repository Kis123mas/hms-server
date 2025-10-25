from rest_framework import serializers
from rest_framework.validators import UniqueValidator
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from .models import *




class RegisterSerializer(serializers.ModelSerializer):
    password_confirmation = serializers.CharField(write_only=True, required=True)
    role = serializers.CharField(write_only=True, required=False, default='patient')

    class Meta:
        model = CustomUser
        fields = ('email', 'password', 'password_confirmation', 'first_name', 'last_name', 'role')
        extra_kwargs = {
            "password": {"write_only": True},
            "email": {
                "required": True,
                "allow_blank": False,
                "validators": [
                    UniqueValidator(
                        queryset=CustomUser.objects.all(),
                        message="A user with that email already exists."
                    )
                ]
            }
        }

    def validate(self, data):
        errors = {}
        
        # Check password match
        if data.get('password') != data.get('password_confirmation'):
            errors['password'] = ["Passwords do not match."]
            errors['password_confirmation'] = ["Passwords do not match."]
        
        # Check required fields
        required_fields = ['email', 'password', 'first_name', 'last_name']
        for field in required_fields:
            if not data.get(field):
                errors[field] = ["This field is required."]
        
        # Check email format
        if 'email' in data and '@' not in data['email']:
            errors.setdefault('email', []).append("Enter a valid email address.")
        
        if errors:
            raise serializers.ValidationError(errors)
            
        return data

    def validate_role(self, value):
        if not value:
            # If no role provided, default to 'patient'
            try:
                return Group.objects.get(name='patient')
            except Group.DoesNotExist:
                # Create patient group if it doesn't exist
                return Group.objects.create(name='patient')
                
        try:
            return Group.objects.get(name=value)
        except Group.DoesNotExist:
            raise serializers.ValidationError(
                f"Invalid role '{value}'. Available roles: {list(Group.objects.values_list('name', flat=True))}"
            )

    def create(self, validated_data):
        password = validated_data.pop('password')
        validated_data.pop('password_confirmation', None)
        
        # Get the role (already validated as Group instance)
        role = validated_data.pop('role', None)
        if not role:
            role = Group.objects.get(name='patient')
        
        user = CustomUser.objects.create(**validated_data, role=role)
        user.set_password(password)
        user.save()
        return user


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)
    password = serializers.CharField(required=True, write_only=True)

    def validate(self, data):
        email = data.get('email')
        password = data.get('password')

        if email and password:
            user = authenticate(request=self.context.get('request'), 
                               email=email, 
                               password=password)
            if not user:
                raise serializers.ValidationError("Unable to log in with provided credentials.")
        else:
            raise serializers.ValidationError("Must include 'email' and 'password'.")

        data['user'] = user
        return data


class UserSerializer(serializers.ModelSerializer):
    role = serializers.SerializerMethodField()

    class Meta:
        model = CustomUser
        fields = ('id', 'email', 'first_name', 'last_name', 'is_staff', 'is_superuser', 'role')
        read_only_fields = ('is_staff', 'is_superuser')

    def get_role(self, obj):
        if obj.role:
            return {'id': obj.role.id, 'name': obj.role.name}
        return None



class ForgotPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)


class ResetPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)
    code = serializers.CharField(required=True)
    new_password = serializers.CharField(write_only=True, required=True)
    confirm_password = serializers.CharField(write_only=True, required=True)

    def validate(self, data):
        if data.get('new_password') != data.get('confirm_password'):
            raise serializers.ValidationError("Passwords do not match.")
        return data


class GoogleAuthSerializer(serializers.Serializer):
    id_token = serializers.CharField(required=True)

