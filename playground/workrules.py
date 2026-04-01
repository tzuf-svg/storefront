from rest_framework import serializers
from django.db.models import Q
from .models import ListTzuf, RESTRICTED_CATEGORIES


def validate_category_logic(value, user):
    if value in RESTRICTED_CATEGORIES and not user.is_superuser:
        raise serializers.ValidationError("Only managers can choose 'urgent' and 'management'")
    return value


def get_visible_tasks(user):
    if user.is_superuser:
        return ListTzuf.objects.all()
    return ListTzuf.objects.filter(Q(owner=user) | Q(coworker=user))
