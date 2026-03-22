from .serializers import ListTzufSerializer, UserSerializer
from .models import ListTzuf, WebhookEvent
from .permissions import IsAdmin, IsStaff, IsStaffOrReadOnly
from .workrules import validate_task_view
from .tasks import process_webhook_event
from rest_framework import generics, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.reverse import reverse
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout
from django.db.models import Q
from django.conf import settings



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


@api_view(['POST'])
@permission_classes([])
def webhook_receiver(request):
    # validate secret header
    secret = request.headers.get('X-Webhook-Secret')
    if secret != settings.WEBHOOK_SECRET:
        return Response({'error': 'Invalid secret'}, status=403)

    # store the event
    event = WebhookEvent.objects.create(
        payload=request.data,
        status='pending'
    )
    
    # sends to Celery
    process_webhook_event.delay(event.id)

    return Response({'id': event.id, 'status': 'received'}, status=201)



class TaskListTzufCreate(generics.ListCreateAPIView):
    serializer_class = ListTzufSerializer
    permission_classes = [IsStaff]

    def get_queryset(self):
        user = self.request.user
        return validate_task_view(self, user)
        '''
        # admin permissions 
        if user.is_superuser:
            return ListTzuf.objects.all()
        else:
            return ListTzuf.objects.filter(Q(owner=self.request.user) | Q(coworker=self.request.user))
        '''
        

    def perform_create(self, serializer):
        # save task
        serializer.save(owner=self.request.user)



class TaskListTzufRetrieveUpdateDestroy(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = ListTzufSerializer
    permission_classes = [IsStaff]    
    lookup_field = "pk"

    def get_queryset(self):
        # admin permissions
        user = self.request.user
        if user.is_superuser:
            return ListTzuf.objects.all()
        else:
            return ListTzuf.objects.filter(Q(owner=self.request.user) | Q(coworker=self.request.user))


# the list
def task_list_view(request):
    if request.user.is_superuser:
        tasks = ListTzuf.objects.all()     
    else:
        tasks = ListTzuf.objects.exclude(category='management')
    return render(request, 'task_list.html', {'tasks': tasks})


# Users view
class UserView(generics.RetrieveAPIView):
    serializer_class = UserSerializer
    permission_classes = [IsStaff] 

    def get_object(self):
        return self.request.user








'''''
# Users list
def user_list_view(request):
    users = User.objects.all()
    return render(request, 'user_list.html', {'users': users})


'''
