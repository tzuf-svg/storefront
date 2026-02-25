from django.urls import path
from .import views

urlpatterns = [
    #path("",views.api_root),
    path("listitems/", views.TaskListTzufCreate.as_view(), name="listitem-view-create"),
    #path("listitems/<int:pk>/", views.TaskListTzufRetrieveUpdateDestroy.as_view(), name="update",),
    #path('task-list/', views.task_list_view, name='task-list'),
    #path('user-list/', views.user_list_view, name='user-list'),
    path('tasks/<int:pk>/update-manual/', views.update_task_manual, name='task-update-manual'),
]