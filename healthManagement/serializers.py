from rest_framework import serializers
from django.contrib.auth import get_user_model
from healthManagement.models import Profile

APPLICATIONS_USER_MODEL = get_user_model()

class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profile
        fields = ['phone_number', 'address', 'date_of_birth', 'profile_picture']
        extra_kwargs = {
            'profile_picture': {'required': False}
        }

class PatientUserSerializer(serializers.ModelSerializer):
    role = serializers.SerializerMethodField()
    profile = ProfileSerializer(read_only=True)

    class Meta:
        model = APPLICATIONS_USER_MODEL
        fields = [
            'id', 
            'email', 
            'first_name', 
            'last_name', 
            'role',
            'profile'  # Include the nested profile
        ]
    
    def get_role(self, obj):
        return obj.role.name if obj.role else None