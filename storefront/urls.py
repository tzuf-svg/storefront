from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView
from django.contrib.auth import views as auth_views
from playground.views import force_logout

urlpatterns = [
    path('', RedirectView.as_view(url='/login/')),
    path('login/', auth_views.LoginView.as_view(template_name='login.html'), name='login'),
    path('accounts/', include('allauth.urls')),
    path('admin/', admin.site.urls),
    path("tasklist/", include("playground.urls")),
    path('api-auth/logout/', force_logout, name='logout'),
    path('api-auth/', include('rest_framework.urls')),
]
