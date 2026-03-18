from rest_framework import serializers
from .models import ListTzuf, Tag
from .workrules import validate_category_logic
from django.contrib.auth.models import User


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'is_staff']


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ['id', 'name']


class ListTzufSerializer(serializers.ModelSerializer):
    owner = serializers.ReadOnlyField(source='owner.username')
    tags = serializers.PrimaryKeyRelatedField(queryset=Tag.objects.all(), many=True)
    coworker = UserSerializer(read_only=True, many=True)
    coworker_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(),
        source='coworker',
        write_only=True,
        many=True,
        required=False
    )

    class Meta:
        model = ListTzuf
        fields = ["id", "title", "category", "content", "completed", "completed_at", "created_at", "owner", "tags", "coworker", "coworker_id", "due_date" ]

    def validate_category(self, value):
        user = self.context['request'].user
        return validate_category_logic(value, user)
    


     
