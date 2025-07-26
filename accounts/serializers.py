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
        if data['password'] != data['password_confirmation']:
            raise serializers.ValidationError("Passwords do not match.")
        return data

    def validate_role(self, value):
        try:
            return Group.objects.get(name=value)  # Return Group instance
        except Group.DoesNotExist:
            raise serializers.ValidationError(f"Invalid role name '{value}'. Role must be an existing Group.")

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



