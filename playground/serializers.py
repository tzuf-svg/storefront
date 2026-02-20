from rest_framework import serializers
from .models import ListTzuf
from .workrules import validate_category_logic


class ListTzufSerializer(serializers.ModelSerializer):
    owner = serializers.ReadOnlyField(source='owner.username')

    class Meta:
        model = ListTzuf
        fields = ["id", "title", "category", "content", "completed", "created_at", "owner"]

    def validate_category(self, value):
        user = self.context['request'].user
        return validate_category_logic(value, user)
    
    
        
