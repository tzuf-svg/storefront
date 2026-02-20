from rest_framework import serializers
from .models import ListTzuf
from .workrules import validate_category_logic
from django.contrib.auth.models import User



class ListTzufSerializer(serializers.ModelSerializer):
    owner = serializers.ReadOnlyField(source='owner.username')

    class Meta:
        model = ListTzuf
        fields = ["id", "title", "category", "content", "completed", "created_at", "owner"]

    def validate_category(self, value):
        user = self.context['request'].user
        return validate_category_logic(value, user)
    

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'is_staff']
        
