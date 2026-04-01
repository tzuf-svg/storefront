import json
from .serializers import ListTzufSerializer, UserSerializer
from .models import ListTzuf, WebhookEvent
from .permissions import IsStaff
from .workrules import get_visible_tasks
from .tasks import process_webhook_event
from .monday import validate_monday_signature, normalize_monday_event
from .sandbox import run_in_sandbox
from .providers import BaseProvider
from rest_framework import generics
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.reverse import reverse
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import render, redirect
from django.contrib.auth import logout
from django.conf import settings
from allauth.socialaccount.models import SocialAccount
from django.contrib.auth import logout as django_logout


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
    request.session.flush()
    logout(request)
    return redirect('/accounts/google/login/')


def force_logout(request):
    if request.user.is_authenticated:
        SocialAccount.objects.filter(user=request.user).update(extra_data={})
    django_logout(request)
    return redirect('/login/')


@api_view(['POST'])
@permission_classes([])
def webhook_receiver(request):
    if request.headers.get('Authorization'):
        if not validate_monday_signature(request):
            return Response({'error': 'Invalid signature'}, status=403)

        monday_event = normalize_monday_event(request.data)
        if monday_event is None:
            return Response({'status': 'ignored'}, status=200)

        try:
            task = ListTzuf.objects.get(title=monday_event.item_name)
        except ListTzuf.DoesNotExist:
            return Response({'error': f'Task "{monday_event.item_name}" not found'}, status=404)

        if task.completed:
            return Response({'error': 'Task is already completed'}, status=409)

        provider = BaseProvider(title=task.title, completed=task.completed)
        event = WebhookEvent.objects.create(payload=request.data, status='pending')

        result = run_in_sandbox(monday_event.code, provider.to_dict())
        if not result.success:
            event.status = 'failed'
            event.save()
            return Response({'error': 'Sandbox execution failed', 'detail': result.error}, status=500)

        sandbox_data = json.loads(result.output)
        task.completed = sandbox_data['completed']
        task.save()

        event.status = 'processed'
        event.save()
        return Response({'id': event.id, 'status': 'received', 'task': sandbox_data}, status=201)

    secret = request.headers.get('X-Webhook-Secret')
    if secret != settings.WEBHOOK_SECRET:
        return Response({'error': 'Invalid secret'}, status=403)

    event = WebhookEvent.objects.create(payload=request.data, status='pending')
    process_webhook_event.delay(event.id)
    return Response({'id': event.id, 'status': 'received'}, status=201)


class TaskListTzufCreate(generics.ListCreateAPIView):
    serializer_class = ListTzufSerializer
    permission_classes = [IsStaff]

    def get_queryset(self):
        return get_visible_tasks(self.request.user)

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)


class TaskListTzufRetrieveUpdateDestroy(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = ListTzufSerializer
    permission_classes = [IsStaff]
    lookup_field = "pk"

    def get_queryset(self):
        return get_visible_tasks(self.request.user)


def task_list_view(request):
    if request.user.is_superuser:
        tasks = ListTzuf.objects.all()
    else:
        tasks = ListTzuf.objects.exclude(category='management')
    return render(request, 'task_list.html', {'tasks': tasks})


class UserView(generics.RetrieveAPIView):
    serializer_class = UserSerializer
    permission_classes = [IsStaff]

    def get_object(self):
        return self.request.user
