from rest_framework import serializers
from .models import ListTzuf
from .workrules import validate_category_logic
from django.contrib.auth.models import User

class ListTzufSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    title = serializers.CharField(required=True, max_length=100)
    categories = serializers.ChoiceField(choices=ListTzuf.CATEGORY_CHOICES, default="work") 
    completed = serializers.BooleanField(required=False, default=False)
    completed_at = serializers.DateTimeField(allow_null=True, required=False, format="%Y-%m-%d %H:%M")
    owner = serializers.ReadOnlyField(source='owner.username')

    def create(self, validated_data):

        #Create and return a new Task
        return ListTzuf.objects.create(**validated_data)

    def update(self, instance, validated_data):

        #Update and return an existing Task
        instance.title = validated_data.get("title", instance.title)
        instance.categories = validated_data.get("categories", instance.categories)
        instance.completed = validated_data.get("completed", instance.completed)
        instance.completed_at = validated_data.get("completed_at", instance.completed_at)
        instance.save()
        return instance

























'''
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
        
'''