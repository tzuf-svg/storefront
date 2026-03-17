from django.shortcuts import render, redirect
from .serializers import ListTzufSerializer, UserSerializer
from .models import ListTzuf
from rest_framework import generics, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.reverse import reverse
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout



@api_view(["GET"])
def api_root(request, format=None):
    return Response(
        {
            "new-task": reverse("listitem-view-create", request=request, format=format),
            "task-list": reverse("task-list", request=request, format=format),
        }
    )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout_view(request):
    request.session.flush()       # destroys session + clears cookie
    logout(request)               # Django logout
    return redirect('/accounts/google/login/')



class TaskListTzufCreate(generics.ListCreateAPIView):
    serializer_class = ListTzufSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        
        # permissions
        if user.is_staff:
            return ListTzuf.objects.all()
        
        # staf sees 'management'
        return ListTzuf.objects.exclude(category='management')

    def perform_create(self, serializer):
        # save task
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
class UserView(generics.RetrieveAPIView):
    serializer_class = UserSerializer

    def get_object(self):
        return self.request.user








'''''
# Users list
def user_list_view(request):
    users = User.objects.all()
    return render(request, 'user_list.html', {'users': users})


'''
