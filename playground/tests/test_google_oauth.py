import pytest
from unittest.mock import MagicMock

from django.conf import settings
from django.test import RequestFactory

from allauth.socialaccount.models import SocialAccount
from allauth.socialaccount.signals import social_account_removed

from playground.factories import UserFactory


@pytest.mark.django_db
class TestGoogleOAuth:

    def test_unauthenticated_redirects_to_login(self, django_client):
        response = django_client.get('/')
        assert response.status_code in (301, 302)

    def test_login_redirect_url_points_to_tasklist(self):
        assert settings.LOGIN_REDIRECT_URL == '/tasklist/'

    def test_logout_view_flushes_session(self, django_client):
        staff = UserFactory(is_staff=True, is_superuser=False)
        django_client.force_login(staff)
        assert '_auth_user_id' in django_client.session
        django_client.post('/tasklist/logout/')
        assert '_auth_user_id' not in django_client.session

    def test_force_logout_clears_social_account_extra_data(self, django_client):
        staff = UserFactory(is_staff=True, is_superuser=False)
        SocialAccount.objects.create(
            user=staff,
            provider='google',
            uid='123',
            extra_data={'token': 'abc'},
        )
        django_client.force_login(staff)
        django_client.post('/api-auth/logout/')
        sa = SocialAccount.objects.get(user=staff)
        assert sa.extra_data == {}

    def test_social_account_removed_signal_fires(self):
        staff = UserFactory(is_staff=True, is_superuser=False)
        sa = SocialAccount.objects.create(
            user=staff,
            provider='google',
            uid='999',
            extra_data={},
        )
        handler = MagicMock()
        social_account_removed.connect(handler)
        try:
            request = RequestFactory().get('/')
            request.user = staff
            social_account_removed.send(
                sender=SocialAccount,
                request=request,
                socialaccount=sa,
            )
            handler.assert_called_once()
        finally:
            social_account_removed.disconnect(handler)
