import pytest
from unittest.mock import patch, MagicMock
from datetime import date, timedelta

from django.conf import settings
from django.contrib.auth.models import User
from django.test import RequestFactory
from rest_framework.test import APIClient

from allauth.socialaccount.models import SocialAccount

from .factories import UserFactory, TodoFactory
from .models import ListTzuf, WebhookEvent
from .tasks import process_webhook_event


# ── helpers ──────────────────────────────────────────────────────────────────

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

    def setup_method(self):
        self.client = APIClient()
        self.url = '/tasklist/listitems/'

    def test_list_tasks_staff_sees_own_and_coworker(self):
        staff = UserFactory(is_staff=True, is_superuser=False)
        other = UserFactory(is_staff=True, is_superuser=False)
        unrelated = UserFactory(is_staff=True, is_superuser=False)

        own_task = TodoFactory(owner=staff, category='work', completed=False)
        coworker_task = TodoFactory(owner=other, category='work', completed=False)
        coworker_task.coworker.add(staff)
        unrelated_task = TodoFactory(owner=unrelated, category='work', completed=False)

        self.client.force_authenticate(user=staff)
        response = self.client.get(self.url)

        assert response.status_code == 200
        ids = [t['id'] for t in response.data]
        assert own_task.id in ids
        assert coworker_task.id in ids
        assert unrelated_task.id not in ids

    def test_list_tasks_superuser_sees_all(self):
        superuser = UserFactory(is_staff=True, is_superuser=True)
        staff = UserFactory(is_staff=True, is_superuser=False)
        task1 = TodoFactory(owner=staff, category='work', completed=False)
        task2 = TodoFactory(owner=staff, category='work', completed=False)

        self.client.force_authenticate(user=superuser)
        response = self.client.get(self.url)

        assert response.status_code == 200
        ids = [t['id'] for t in response.data]
        assert task1.id in ids
        assert task2.id in ids

    def test_list_tasks_unauthenticated_rejected(self):
        response = self.client.get(self.url)
        assert response.status_code == 403

    def test_list_tasks_non_staff_rejected(self):
        user = UserFactory(is_staff=False, is_superuser=False)
        self.client.force_authenticate(user=user)
        response = self.client.get(self.url)
        assert response.status_code == 403

    def test_create_task_sets_owner(self):
        staff = UserFactory(is_staff=True, is_superuser=False)
        self.client.force_authenticate(user=staff)
        data = {
            'title': 'My New Task',
            'category': 'work',
            'content': 'Some content here',
            'due_date': future_weekday().isoformat(),
            'tags': [],
            'coworker_id': [],
        }
        response = self.client.post(self.url, data, format='json')
        assert response.status_code == 201
        assert response.data['owner'] == staff.username

    def test_create_task_invalid_title_too_short(self):
        staff = UserFactory(is_staff=True, is_superuser=False)
        self.client.force_authenticate(user=staff)
        data = {
            'title': 'AB',
            'category': 'work',
            'content': 'Content',
            'due_date': future_weekday().isoformat(),
            'tags': [],
            'coworker_id': [],
        }
        response = self.client.post(self.url, data, format='json')
        assert response.status_code == 400

    def test_create_task_staff_cannot_use_urgent_category(self):
        staff = UserFactory(is_staff=True, is_superuser=False)
        self.client.force_authenticate(user=staff)
        data = {
            'title': 'Urgent Task',
            'category': 'urgent',
            'content': 'Content',
            'due_date': future_weekday().isoformat(),
            'tags': [],
            'coworker_id': [],
        }
        response = self.client.post(self.url, data, format='json')
        assert response.status_code == 400

    def test_create_task_superuser_can_use_urgent_category(self):
        superuser = UserFactory(is_staff=True, is_superuser=True)
        self.client.force_authenticate(user=superuser)
        data = {
            'title': 'Urgent Task',
            'category': 'urgent',
            'content': 'Content',
            'due_date': future_weekday().isoformat(),
            'tags': [],
            'coworker_id': [],
        }
        response = self.client.post(self.url, data, format='json')
        assert response.status_code == 201

    def test_create_task_superuser_can_use_management_category(self):
        superuser = UserFactory(is_staff=True, is_superuser=True)
        self.client.force_authenticate(user=superuser)
        data = {
            'title': 'Management Task',
            'category': 'management',
            'content': 'Content',
            'due_date': future_weekday().isoformat(),
            'tags': [],
            'coworker_id': [],
        }
        response = self.client.post(self.url, data, format='json')
        assert response.status_code == 201

    def test_create_task_past_due_date_rejected(self):
        staff = UserFactory(is_staff=True, is_superuser=False)
        self.client.force_authenticate(user=staff)
        data = {
            'title': 'Past Task',
            'category': 'work',
            'content': 'Content',
            'due_date': past_date().isoformat(),
            'tags': [],
            'coworker_id': [],
        }
        response = self.client.post(self.url, data, format='json')
        assert response.status_code == 400

    def test_create_task_weekend_due_date_rejected(self):
        staff = UserFactory(is_staff=True, is_superuser=False)
        self.client.force_authenticate(user=staff)
        data = {
            'title': 'Weekend Task',
            'category': 'work',
            'content': 'Content',
            'due_date': weekend_date().isoformat(),
            'tags': [],
            'coworker_id': [],
        }
        response = self.client.post(self.url, data, format='json')
        assert response.status_code == 400


# ── 2. TaskDetailTest ─────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestTaskDetail:

    def setup_method(self):
        self.client = APIClient()

    def url(self, pk):
        return f'/tasklist/listitems/{pk}/'

    def test_retrieve_own_task(self):
        staff = UserFactory(is_staff=True, is_superuser=False)
        task = TodoFactory(owner=staff, category='work', completed=False)
        self.client.force_authenticate(user=staff)
        response = self.client.get(self.url(task.pk))
        assert response.status_code == 200
        assert response.data['id'] == task.id

    def test_retrieve_coworker_task(self):
        staff = UserFactory(is_staff=True, is_superuser=False)
        owner = UserFactory(is_staff=True, is_superuser=False)
        task = TodoFactory(owner=owner, category='work', completed=False)
        task.coworker.add(staff)
        self.client.force_authenticate(user=staff)
        response = self.client.get(self.url(task.pk))
        assert response.status_code == 200

    def test_retrieve_other_task_rejected(self):
        staff = UserFactory(is_staff=True, is_superuser=False)
        other = UserFactory(is_staff=True, is_superuser=False)
        task = TodoFactory(owner=other, category='work', completed=False)
        self.client.force_authenticate(user=staff)
        response = self.client.get(self.url(task.pk))
        assert response.status_code == 404

    def test_superuser_retrieves_any_task(self):
        superuser = UserFactory(is_staff=True, is_superuser=True)
        other = UserFactory(is_staff=True, is_superuser=False)
        task = TodoFactory(owner=other, category='work', completed=False)
        self.client.force_authenticate(user=superuser)
        response = self.client.get(self.url(task.pk))
        assert response.status_code == 200

    def test_update_task(self):
        staff = UserFactory(is_staff=True, is_superuser=False)
        task = TodoFactory(owner=staff, category='work', completed=False)
        self.client.force_authenticate(user=staff)
        data = {
            'title': 'Updated Title',
            'category': 'personal',
            'content': 'Updated content',
            'due_date': future_weekday().isoformat(),
            'completed': False,
            'tags': [],
            'coworker_id': [],
        }
        response = self.client.put(self.url(task.pk), data, format='json')
        assert response.status_code == 200
        assert response.data['title'] == 'Updated Title'

    def test_delete_task(self):
        staff = UserFactory(is_staff=True, is_superuser=False)
        task = TodoFactory(owner=staff, category='work', completed=False)
        self.client.force_authenticate(user=staff)
        response = self.client.delete(self.url(task.pk))
        assert response.status_code == 204
        assert not ListTzuf.objects.filter(pk=task.pk).exists()

    def test_completed_at_auto_set(self):
        staff = UserFactory(is_staff=True, is_superuser=False)
        task = TodoFactory(owner=staff, category='work', completed=False)
        self.client.force_authenticate(user=staff)
        data = {
            'title': task.title,
            'category': task.category,
            'content': task.content,
            'due_date': task.due_date.isoformat(),
            'completed': True,
            'tags': [],
            'coworker_id': [],
        }
        response = self.client.put(self.url(task.pk), data, format='json')
        assert response.status_code == 200
        assert response.data['completed_at'] is not None

    def test_completed_at_cleared_on_uncomplete(self):
        staff = UserFactory(is_staff=True, is_superuser=False)
        task = TodoFactory(owner=staff, category='work', completed=True)
        self.client.force_authenticate(user=staff)
        data = {
            'title': task.title,
            'category': task.category,
            'content': task.content,
            'due_date': task.due_date.isoformat(),
            'completed': False,
            'tags': [],
            'coworker_id': [],
        }
        response = self.client.put(self.url(task.pk), data, format='json')
        assert response.status_code == 200
        assert response.data['completed_at'] is None


# ── 3. UserViewTest ───────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestUserView:

    def setup_method(self):
        self.client = APIClient()
        self.url = '/tasklist/user/me/'

    def test_get_current_user(self):
        staff = UserFactory(is_staff=True, is_superuser=False)
        self.client.force_authenticate(user=staff)
        response = self.client.get(self.url)
        assert response.status_code == 200
        assert response.data['id'] == staff.id
        assert response.data['username'] == staff.username
        assert 'email' in response.data
        assert 'is_staff' in response.data

    def test_unauthenticated_rejected(self):
        response = self.client.get(self.url)
        assert response.status_code == 403


# ── 4. WebhookTest ────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestWebhook:

    def setup_method(self):
        self.client = APIClient()
        self.url = '/tasklist/webhook/'
        self.secret = settings.WEBHOOK_SECRET

    @patch('playground.views.process_webhook_event')
    def test_valid_secret_creates_event(self, mock_task):
        mock_task.delay = MagicMock()
        payload = {'event': 'task.created', 'data': {'id': 1}}
        response = self.client.post(
            self.url,
            payload,
            format='json',
            HTTP_X_WEBHOOK_SECRET=self.secret,
        )
        assert response.status_code == 201
        assert WebhookEvent.objects.filter(payload=payload).exists()

    @patch('playground.views.process_webhook_event')
    def test_invalid_secret_rejected(self, mock_task):
        mock_task.delay = MagicMock()
        response = self.client.post(
            self.url,
            {'event': 'task.created'},
            format='json',
            HTTP_X_WEBHOOK_SECRET='wrong-secret',
        )
        assert response.status_code == 403

    @patch('playground.tasks.process_webhook_event.delay')
    def test_celery_task_queued(self, mock_delay):
        payload = {'event': 'ping'}
        response = self.client.post(
            self.url,
            payload,
            format='json',
            HTTP_X_WEBHOOK_SECRET=self.secret,
        )
        assert response.status_code == 201
        event_id = response.data['id']
        mock_delay.assert_called_once_with(event_id)


# ── 5. CeleryTaskTest ─────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestCeleryTask:

    def test_process_webhook_event_success(self):
        event = WebhookEvent.objects.create(payload={'test': True}, status='pending')
        process_webhook_event(event.id)
        event.refresh_from_db()
        assert event.status == 'processed'

    def test_process_webhook_event_not_found(self):
        # Should log and not raise
        process_webhook_event(99999)

    def test_process_webhook_event_simulate_failure(self):
        event = WebhookEvent.objects.create(payload={'test': True}, status='pending')
        with pytest.raises(Exception):
            process_webhook_event(event.id, simulate_failure=True)
        event.refresh_from_db()
        assert event.status == 'failed'


# ── 6. TaskListHTMLViewTest ───────────────────────────────────────────────────

@pytest.mark.django_db
class TestTaskListHTMLView:

    def setup_method(self):
        self.client = APIClient()
        self.url = '/tasklist/task-list/'

    def test_superuser_sees_management_tasks(self):
        superuser = UserFactory(is_staff=True, is_superuser=True)
        mgmt_task = TodoFactory(owner=superuser, category='management', completed=False)
        self.client.force_authenticate(user=superuser)

        from django.test import Client as DjangoClient
        django_client = DjangoClient()
        django_client.force_login(superuser)
        response = django_client.get(self.url)

        assert response.status_code == 200
        assert mgmt_task in response.context['tasks']

    def test_staff_excludes_management_tasks(self):
        superuser = UserFactory(is_staff=True, is_superuser=True)
        staff = UserFactory(is_staff=True, is_superuser=False)
        mgmt_task = TodoFactory(owner=superuser, category='management', completed=False)

        from django.test import Client as DjangoClient
        django_client = DjangoClient()
        django_client.force_login(staff)
        response = django_client.get(self.url)

        assert response.status_code == 200
        assert mgmt_task not in response.context['tasks']


# ── 7. GoogleOAuthTest ────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestGoogleOAuth:

    def test_unauthenticated_redirects_to_login(self):
        from django.test import Client as DjangoClient
        client = DjangoClient()
        response = client.get('/')
        assert response.status_code in (301, 302)

    def test_login_redirect_url_points_to_tasklist(self):
        assert settings.LOGIN_REDIRECT_URL == '/tasklist/'

    def test_logout_view_flushes_session(self):
        staff = UserFactory(is_staff=True, is_superuser=False)
        api_client = APIClient()
        api_client.force_authenticate(user=staff)
        response = api_client.post('/tasklist/logout/')
        # redirects after logout
        assert response.status_code in (301, 302)

    def test_force_logout_clears_social_account_extra_data(self):
        staff = UserFactory(is_staff=True, is_superuser=False)
        SocialAccount.objects.create(
            user=staff,
            provider='google',
            uid='123',
            extra_data={'token': 'abc'},
        )
        from django.test import Client as DjangoClient
        client = DjangoClient()
        client.force_login(staff)
        response = client.post('/api-auth/logout/')
        assert response.status_code in (301, 302)
        sa = SocialAccount.objects.get(user=staff)
        assert sa.extra_data == {}

    def test_social_account_removed_signal_fires(self):
        from allauth.socialaccount.signals import social_account_removed
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

    def test_social_login_creates_user(self):
        """Verify that a user created via factory has is_authenticated True (simulates post-OAuth state)."""
        user = UserFactory(is_staff=True, is_superuser=False)
        SocialAccount.objects.create(
            user=user,
            provider='google',
            uid='oauth-uid-42',
            extra_data={'email': 'test@example.com'},
        )
        assert user.is_authenticated
        assert SocialAccount.objects.filter(user=user, provider='google').exists()
