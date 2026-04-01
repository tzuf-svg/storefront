from django.urls import path
from . import views

urlpatterns = [
    path("", views.api_root),
    path("listitems/", views.TaskListTzufCreate.as_view(), name="listitem-view-create"),
    path("listitems/<int:pk>/", views.TaskListTzufRetrieveUpdateDestroy.as_view(), name="update"),
    path('task-list/', views.task_list_view, name='task-list'),
    path('user/me/', views.UserView.as_view(), name='user'),
    path('logout/', views.logout_view, name='logout'),
    path('webhook/', views.webhook_receiver, name='webhook-secret-receiver'),
]
