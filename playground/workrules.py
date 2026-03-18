from rest_framework import serializers


def validate_category_logic(value, user):
    restricted_categories = ['urgent', 'management']
    
    if value in restricted_categories and not user.is_staff:
        
        raise serializers.ValidationError("Only managers can choose 'urgent' and 'management'")
    
    return value