from django.shortcuts import render
from rest_framework import generics, permissions
from .models import ListTzuf
from .serializers import ListTzufSerializer
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.reverse import reverse



@api_view(["GET"])
def api_root(request, format=None):
    return Response(
        {
            "task": reverse("listitem-view-create", request=request, format=format),
            "list": reverse("task-list", request=request, format=format),
        }
    )


class TaskListTzufCreate(generics.ListCreateAPIView):
    serializer_class = ListTzufSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        
        # אם המשתמש הוא מנהל (Staff) - הוא רואה הכל, כולל ניהול
        if user.is_staff:
            return ListTzuf.objects.all()
        
        # אם המשתמש רגיל - הוא רואה הכל חוץ מקטגוריית management
        return ListTzuf.objects.exclude(category='management')

    def perform_create(self, serializer):
        # הוספה קבועה: שיוך המשימה למשתמש שיצר אותה
        serializer.save(owner=self.request.user)


class TaskListTzufRetrieveUpdateDestroy(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = ListTzufSerializer    
    lookup_field = "pk"

    def get_queryset(self):
        return ListTzuf.objects.filter(owner=self.request.user)


def task_list_view(request):
    tasks = ListTzuf.objects.all()
    return render(request, 'task_list.html', {'tasks': tasks})





