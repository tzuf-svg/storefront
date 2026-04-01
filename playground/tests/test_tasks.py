import pytest
from datetime import date, timedelta

from django.urls import reverse

from playground.factories import UserFactory, TodoFactory
from playground.models import ListTzuf


# ── date helpers ──────────────────────────────────────────────────────────────

def next_weekday(d=None, offset_days=7):
    if d is None:
        d = date.today()
    result = d + timedelta(days=offset_days)
    while result.weekday() >= 5:
        result += timedelta(days=1)
    return result


def future_weekday():
    return next_weekday()


def past_date():
    return date.today() - timedelta(days=1)


def weekend_date():
    d = date.today() + timedelta(days=1)
    while d.weekday() != 5:
        d += timedelta(days=1)
    return d


# ── TestTaskListCreate ────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestTaskListCreate:

    def test_list_tasks_staff_sees_own_and_coworker(self, api_client):
        staff = UserFactory(is_staff=True, is_superuser=False)
        other = UserFactory(is_staff=True, is_superuser=False)
        unrelated = UserFactory(is_staff=True, is_superuser=False)

        own_task = TodoFactory(owner=staff)
        coworker_task = TodoFactory(owner=other)
        coworker_task.coworker.add(staff)
        unrelated_task = TodoFactory(owner=unrelated)

        api_client.force_authenticate(user=staff)
        response = api_client.get(reverse('listitem-view-create'))

        assert response.status_code == 200
        ids = [t['id'] for t in response.data]
        assert own_task.id in ids
        assert coworker_task.id in ids
        assert unrelated_task.id not in ids

    def test_list_tasks_superuser_sees_all(self, api_client):
        superuser = UserFactory(is_staff=True, is_superuser=True)
        staff = UserFactory(is_staff=True, is_superuser=False)
        task1 = TodoFactory(owner=staff)
        task2 = TodoFactory(owner=staff)

        api_client.force_authenticate(user=superuser)
        response = api_client.get(reverse('listitem-view-create'))

        assert response.status_code == 200
        ids = [t['id'] for t in response.data]
        assert task1.id in ids
        assert task2.id in ids

    def test_list_tasks_unauthenticated_rejected(self, api_client):
        response = api_client.get(reverse('listitem-view-create'))
        assert response.status_code == 403

    def test_list_tasks_non_staff_rejected(self, api_client):
        user = UserFactory(is_staff=False, is_superuser=False)
        api_client.force_authenticate(user=user)
        response = api_client.get(reverse('listitem-view-create'))
        assert response.status_code == 403

    def test_create_task_sets_owner(self, api_client):
        staff = UserFactory(is_staff=True, is_superuser=False)
        api_client.force_authenticate(user=staff)
        data = {
            'title': 'My New Task',
            'category': 'work',
            'content': 'Some content here',
            'due_date': future_weekday().isoformat(),
            'tags': [],
            'coworker_id': [],
        }
        response = api_client.post(reverse('listitem-view-create'), data, format='json')
        assert response.status_code == 201
        assert response.data['owner'] == staff.username

    def test_create_task_invalid_title_too_short(self, api_client):
        staff = UserFactory(is_staff=True, is_superuser=False)
        api_client.force_authenticate(user=staff)
        data = {
            'title': 'AB',
            'category': 'work',
            'content': 'Content',
            'due_date': future_weekday().isoformat(),
            'tags': [],
            'coworker_id': [],
        }
        response = api_client.post(reverse('listitem-view-create'), data, format='json')
        assert response.status_code == 400

    @pytest.mark.parametrize("category,is_superuser,expected_status", [
        ("urgent",     False, 400),
        ("management", False, 400),
        ("urgent",     True,  201),
        ("management", True,  201),
    ])
    def test_category_restrictions(self, api_client, category, is_superuser, expected_status):
        user = UserFactory(is_staff=True, is_superuser=is_superuser)
        api_client.force_authenticate(user=user)
        data = {
            'title': f'{category.capitalize()} Task',
            'category': category,
            'content': 'Content',
            'due_date': future_weekday().isoformat(),
            'tags': [],
            'coworker_id': [],
        }
        response = api_client.post(reverse('listitem-view-create'), data, format='json')
        assert response.status_code == expected_status

    @pytest.mark.parametrize("due_date_fn", [past_date, weekend_date])
    def test_create_task_invalid_due_date_rejected(self, api_client, due_date_fn):
        staff = UserFactory(is_staff=True, is_superuser=False)
        api_client.force_authenticate(user=staff)
        data = {
            'title': 'Task Title',
            'category': 'work',
            'content': 'Content',
            'due_date': due_date_fn().isoformat(),
            'tags': [],
            'coworker_id': [],
        }
        response = api_client.post(reverse('listitem-view-create'), data, format='json')
        assert response.status_code == 400


# ── TestTaskDetail ────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestTaskDetail:

    def test_retrieve_own_task(self, api_client):
        staff = UserFactory(is_staff=True, is_superuser=False)
        task = TodoFactory(owner=staff)
        api_client.force_authenticate(user=staff)
        response = api_client.get(reverse('update', args=[task.pk]))
        assert response.status_code == 200
        assert response.data['id'] == task.id

    def test_retrieve_coworker_task(self, api_client):
        staff = UserFactory(is_staff=True, is_superuser=False)
        owner = UserFactory(is_staff=True, is_superuser=False)
        task = TodoFactory(owner=owner)
        task.coworker.add(staff)
        api_client.force_authenticate(user=staff)
        response = api_client.get(reverse('update', args=[task.pk]))
        assert response.status_code == 200

    def test_retrieve_other_task_rejected(self, api_client):
        staff = UserFactory(is_staff=True, is_superuser=False)
        other = UserFactory(is_staff=True, is_superuser=False)
        task = TodoFactory(owner=other)
        api_client.force_authenticate(user=staff)
        response = api_client.get(reverse('update', args=[task.pk]))
        assert response.status_code == 404

    def test_superuser_retrieves_any_task(self, api_client):
        superuser = UserFactory(is_staff=True, is_superuser=True)
        other = UserFactory(is_staff=True, is_superuser=False)
        task = TodoFactory(owner=other)
        api_client.force_authenticate(user=superuser)
        response = api_client.get(reverse('update', args=[task.pk]))
        assert response.status_code == 200

    def test_update_task(self, api_client):
        staff = UserFactory(is_staff=True, is_superuser=False)
        task = TodoFactory(owner=staff)
        api_client.force_authenticate(user=staff)
        data = {
            'title': 'Updated Title',
            'category': 'personal',
            'content': 'Updated content',
            'due_date': future_weekday().isoformat(),
            'completed': False,
            'tags': [],
            'coworker_id': [],
        }
        response = api_client.put(reverse('update', args=[task.pk]), data, format='json')
        assert response.status_code == 200
        assert response.data['title'] == 'Updated Title'

    def test_delete_task(self, api_client):
        staff = UserFactory(is_staff=True, is_superuser=False)
        task = TodoFactory(owner=staff)
        api_client.force_authenticate(user=staff)
        response = api_client.delete(reverse('update', args=[task.pk]))
        assert response.status_code == 204
        assert not ListTzuf.objects.filter(pk=task.pk).exists()

    @pytest.mark.parametrize("initial_completed,set_completed,expect_set", [
        (False, True,  True),
        (True,  False, False),
    ])
    def test_completed_at_toggling(self, api_client, initial_completed, set_completed, expect_set):
        staff = UserFactory(is_staff=True, is_superuser=False)
        task = TodoFactory(owner=staff, completed=initial_completed)
        api_client.force_authenticate(user=staff)
        data = {
            'title': task.title,
            'category': task.category,
            'content': task.content,
            'due_date': task.due_date.isoformat(),
            'completed': set_completed,
            'tags': [],
            'coworker_id': [],
        }
        response = api_client.put(reverse('update', args=[task.pk]), data, format='json')
        assert response.status_code == 200
        assert (response.data['completed_at'] is not None) == expect_set
