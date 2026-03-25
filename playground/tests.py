import pytest
from datetime import date, timedelta
from unittest.mock import patch, MagicMock

from django.conf import settings
from django.test import RequestFactory
from django.urls import reverse

from allauth.socialaccount.models import SocialAccount
from allauth.socialaccount.signals import social_account_removed

from .factories import UserFactory, TodoFactory, WebhookEventFactory
from .models import ListTzuf, WebhookEvent
from .tasks import process_webhook_event


# ── helpers ───────────────────────────────────────────────────────────────────

def next_weekday(d=None, offset_days=7):
    """Return a future weekday date offset_days from d (skipping weekends)."""
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
    """Return the next Saturday from today."""
    d = date.today() + timedelta(days=1)
    while d.weekday() != 5:
        d += timedelta(days=1)
    return d


# ── 1. TaskListCreateTest ─────────────────────────────────────────────────────

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


# ── 2. TaskDetailTest ─────────────────────────────────────────────────────────

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
        (False, True,  True),   # marking complete sets completed_at
        (True,  False, False),  # un-completing clears completed_at
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


# ── 3. UserViewTest ───────────────────────────────────────────────────────────

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


# ── 4. WebhookTest ────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestWebhook:

    @patch('playground.views.process_webhook_event')
    def test_valid_secret_creates_event(self, mock_task, api_client):
        mock_task.delay = MagicMock()
        payload = {'event': 'task.created', 'data': {'id': 1}}
        response = api_client.post(
            reverse('webhook-secret-receiver'),
            payload,
            format='json',
            HTTP_X_WEBHOOK_SECRET=settings.WEBHOOK_SECRET,
        )
        assert response.status_code == 201
        assert WebhookEvent.objects.filter(payload=payload).exists()

    @patch('playground.views.process_webhook_event')
    def test_invalid_secret_rejected(self, mock_task, api_client):
        mock_task.delay = MagicMock()
        response = api_client.post(
            reverse('webhook-secret-receiver'),
            {'event': 'task.created'},
            format='json',
            HTTP_X_WEBHOOK_SECRET='wrong-secret',
        )
        assert response.status_code == 403

    @patch('playground.tasks.process_webhook_event.delay')
    def test_celery_task_queued(self, mock_delay, api_client):
        payload = {'event': 'ping'}
        response = api_client.post(
            reverse('webhook-secret-receiver'),
            payload,
            format='json',
            HTTP_X_WEBHOOK_SECRET=settings.WEBHOOK_SECRET,
        )
        assert response.status_code == 201
        mock_delay.assert_called_once_with(response.data['id'])


# ── 5. CeleryTaskTest ─────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestCeleryTask:

    def test_process_webhook_event_success(self):
        event = WebhookEventFactory()
        process_webhook_event(event.id)
        event.refresh_from_db()
        assert event.status == 'processed'

    def test_process_webhook_event_not_found(self):
        process_webhook_event(99999)
        assert not WebhookEvent.objects.filter(pk=99999).exists()

    def test_process_webhook_event_simulate_failure(self):
        event = WebhookEventFactory()
        with pytest.raises(Exception):
            process_webhook_event(event.id, simulate_failure=True)
        event.refresh_from_db()
        assert event.status == 'failed'


# ── 6. TaskListHTMLViewTest ───────────────────────────────────────────────────

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


# ── 7. GoogleOAuthTest ────────────────────────────────────────────────────────

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
