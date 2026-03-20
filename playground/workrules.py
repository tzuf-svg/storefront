from rest_framework import serializers
from django.db.models import Q
from .models import ListTzuf


# category permissions
def validate_category_logic(value, user):
    restricted_categories = ['urgent', 'management']
    
    if value in restricted_categories and not user.is_superuser:
        
        raise serializers.ValidationError("Only managers can choose 'urgent' and 'management'")
    
    return value


# admin sees all, staf sees owner and coworker
def validate_task_view(self, user):
        if user.is_superuser:
            return ListTzuf.objects.all()
        else:
            return ListTzuf.objects.filter(
                 Q(owner=self.request.user) | 
                 Q(coworker=self.request.user)
                 )
        


