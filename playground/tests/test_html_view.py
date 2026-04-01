import pytest

from django.urls import reverse

from playground.factories import UserFactory, TodoFactory


@pytest.mark.django_db
class TestTaskListHTMLView:

    def test_superuser_sees_management_tasks(self, django_client):
        superuser = UserFactory(is_staff=True, is_superuser=True)
        mgmt_task = TodoFactory(owner=superuser, management=True)
        django_client.force_login(superuser)
        response = django_client.get(reverse('task-list'))
        assert response.status_code == 200
        assert mgmt_task in response.context['tasks']

    def test_staff_excludes_management_tasks(self, django_client):
        superuser = UserFactory(is_staff=True, is_superuser=True)
        staff = UserFactory(is_staff=True, is_superuser=False)
        mgmt_task = TodoFactory(owner=superuser, management=True)
        django_client.force_login(staff)
        response = django_client.get(reverse('task-list'))
        assert response.status_code == 200
        assert mgmt_task not in response.context['tasks']
