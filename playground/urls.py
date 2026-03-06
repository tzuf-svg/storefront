from django.urls import path
from .import views
from allauth.socialaccount.providers.google.views import GoogleOAuth2Adapter
from dj_rest_auth.registration.views import SocialLoginView


class GoogleLogin(SocialLoginView):
    adapter_class = GoogleOAuth2Adapter

urlpatterns = [
    path('dj-rest-auth/google/', GoogleLogin.as_view(), name='google_login'),
    path("",views.api_root),
    path("listitems/", views.TaskListTzufCreate.as_view(), name="listitem-view-create"),
    path("listitems/<int:pk>/", views.TaskListTzufRetrieveUpdateDestroy.as_view(), name="update",),
    path('task-list/', views.task_list_view, name='task-list'),
]    
    #path('user-list/', views.user_list_view, name='user-list'),


