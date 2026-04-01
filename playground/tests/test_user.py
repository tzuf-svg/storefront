import pytest

from django.urls import reverse

from playground.factories import UserFactory


@pytest.mark.django_db
class TestUserView:

    def test_get_current_user(self, api_client):
        staff = UserFactory(is_staff=True, is_superuser=False)
        api_client.force_authenticate(user=staff)
        response = api_client.get(reverse('user'))
        assert response.status_code == 200
        assert response.data['id'] == staff.id
        assert response.data['username'] == staff.username
        assert 'email' in response.data
        assert 'is_staff' in response.data

    def test_unauthenticated_rejected(self, api_client):
        response = api_client.get(reverse('user'))
        assert response.status_code == 403
