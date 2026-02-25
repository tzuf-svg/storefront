from django.shortcuts import render
from rest_framework import generics, permissions
from .models import ListTzuf
#from .serializers import ListTzufSerializer
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.reverse import reverse
from django.contrib.auth.models import User
#from .serializers import UserSerializer
from django.contrib.auth.decorators import login_required

from rest_framework import status
from django.utils.dateparse import parse_datetime
import json
from rest_framework.views import APIView

'''''
@api_view(["GET"])
def api_root(request, format=None):
    return Response(
        {
            "task": reverse("listitem-view-create", request=request, format=format),
            "task-list": reverse("task-list", request=request, format=format),
            "user-list": reverse("user-list", request=request, format=format),
        }
    )
'''


class TaskListTzufCreate(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        # premissions
        if user.is_staff:
            queryset = ListTzuf.objects.all()
        else:
            queryset = ListTzuf.objects.exclude(category='management')
        
        # make JSON
        data = []
        for task in queryset:
            data.append({
                "id": task.id,
                "title": task.title,
                "category": task.category,
                "owner": task.owner.username if task.owner else "TzufR"
            })
        return Response(data)

    def post(self, request):
        data = request.data 
        # verifecation titel
        title = data.get('title')
        if not title:
            return Response({"error": "Title is missing!"}, status=400)
        
        # create tank
        new_task = ListTzuf.objects.create(
            title=title,
            content=data.get('content', ''),
            category=data.get('category', 'work'),
            owner=request.user 
        )

        return Response({"id": new_task.id, "message": "Task created manually!"}, status=201)



@api_view(["POST", "PATCH"])
def update_task_manual(request, pk):
    try:
        # gets the object and the raw data
        task = ListTzuf.objects.get(pk=pk)
        data = request.data


        # title verification
        if 'title' in data:
            title = data.get('title')
            if not isinstance(title, str) or len(title) > 100:
                return Response({"error": "Title must be a string up to 100 chars"}, status=status.HTTP_400_BAD_REQUEST)
            task.title = title

        # category verification
        if 'category' in data:
            category = data.get('category')
            valid_categories = [choice[0] for choice in ListTzuf.CATEGORY_CHOICES]
            if category not in valid_categories:
                return Response({"error": f"Invalid category. Choose from: {valid_categories}"}, status=status.HTTP_400_BAD_REQUEST)
            task.category = category 

        # completed verification
        if 'completed' in data:
            completed = data.get('completed')
            if not isinstance(completed, bool):
                return Response({"error": "Completed must be true or false"}, status=status.HTTP_400_BAD_REQUEST)
            task.completed = completed     

        # completed_at verification
        if 'completed_at' in data:
            raw_date = data.get('completed_at')
            if raw_date: 
                dt = parse_datetime(raw_date)
                if dt is None:
                    return Response({"error": "Invalid timestamp format. Use ISO 8601"}, status=status.HTTP_400_BAD_REQUEST)
                task.completed_at = dt
            else:
                task.completed_at = None

        # saving the result
        task.save()
        
        return Response({
            "status": "success",
            "message": f"Task '{task.title}' updated",
            "data": {
                "id": task.id,
                "completed": task.completed,
                "completed_at": task.completed_at
            }
        }, status=status.HTTP_200_OK)

    except ListTzuf.DoesNotExist:
        return Response({"error": "Task not found"}, status=status.HTTP_404_NOT_FOUND)























'''
class TaskListTzufCreate(generics.ListCreateAPIView):
    serializer_class = update_task_manual
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


# Users view
class UserListView(generics.ListAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer


# Users list
def user_list_view(request):
    users = User.objects.all()
    return render(request, 'user_list.html', {'users': users})


'''
