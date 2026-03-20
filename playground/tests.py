import django
from django.conf import settings
from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User
from datetime import date, timedelta
from rest_framework import status
from rest_framework.test import force_authenticate, APIRequestFactory, APIClient
from .factories import UserFactory, TodoFactory
from .models import ListTzuf


# Model tests

class TaskListCreateTest(TestCase):

    # create a staff user to test with
    def setUp(self):       
        self.client = APIClient()
        self.user = UserFactory(is_staff=True)
        self.client.force_authenticate(user=self.user)


    def test_create_task(self):
        
        data = {
            'title': 'Test Task',
            'content': 'test',
            'category': 'work',
        }

        # send POST request
        response = self.client.post('/tasklist/listitems/', data)
       
        # check the response
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(ListTzuf.objects.count(), 1)
        self.assertEqual(ListTzuf.objects.get().owner, self.user)


    # completed at test

    def test_completed_at_set_when_completed(self):
        # create a task
        task = ListTzuf.objects.create(
            title='Test Task',
            category='work',
            content='test',
            owner=self.user
        )
        self.assertIsNone(task.completed_at)

        # mark as completed
        task.completed = True
        task.save()
        self.assertIsNotNone(task.completed_at)

    def test_completed_at_cleared_when_uncompleted(self):
        task = ListTzuf.objects.create(
            title='Test Task',
            category='work',
            content='test',
            owner=self.user,
            completed=True
        )
        # uncheck completed
        task.completed = False
        task.save()
        self.assertIsNone(task.completed_at)
        

    # coworker test

    def test_coworker_can_update_task(self):
        # create a coworker user
        coworker = User.objects.create_user(
            username='coworker',
            password='testpass123',
            is_staff=True
        )

        # create a task owned by self.user
        task = ListTzuf.objects.create(
            title='Test Task',
            category='work',
            content='test',
            owner=self.user
        )

        # add coworker to the task
        task.coworker.add(coworker)

        # authenticate as coworker
        self.client.force_authenticate(user=coworker)

        # try to update the task
        response = self.client.patch(
            f'/tasklist/listitems/{task.id}/',
            {'title': 'Updated Title'}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['title'], 'Updated Title')



# Serializer tests

    # due date tests
    def test_due_date_in_past_fails(self):
        data = {
            'title': 'Test Task',
            'category': 'work',
            'content': 'test',
            'due_date': date.today() - timedelta(days=1),  # yesterday
        }
        response = self.client.post('/tasklist/listitems/', data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('due_date', response.data)

    def test_due_date_today_fails(self):
        data = {
            'title': 'Test Task',
            'category': 'work',
            'content': 'test',
            'due_date': date.today(),  # today
        }
        response = self.client.post('/tasklist/listitems/', data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('due_date', response.data)

    def test_due_date_weekend_fails(self):
        # find next Saturday
        today = date.today()
        days_until_saturday = (5 - today.weekday()) % 7 or 7
        saturday = today + timedelta(days=days_until_saturday)
        
        data = {
            'title': 'Test Task',
            'category': 'work',
            'content': 'test',
            'due_date': saturday,
        }
        response = self.client.post('/tasklist/listitems/', data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('due_date', response.data)

    def test_due_date_valid(self):
        # find next weekday at least 2 days from now
        future = date.today() + timedelta(days=2)
        while future.weekday() >= 5:
            future += timedelta(days=1)

        data = {
            'title': 'Test Task',
            'category': 'work',
            'content': 'test',
            'due_date': future,
        }
        response = self.client.post('/tasklist/listitems/', data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)


    # invalid input
    def test_title_too_short(self):
        data = {
            'title': 'ab',  # less than 3 characters
            'category': 'work',
            'content': 'test',
        }
        response = self.client.post('/tasklist/listitems/', data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('title', response.data)

    def test_title_too_long(self):
        data = {
            'title': 'a' * 101,  # more than 100 characters
            'category': 'work',
            'content': 'test',
        }
        response = self.client.post('/tasklist/listitems/', data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('title', response.data)

    def test_invalid_category(self):
        data = {
            'title': 'Test Task',
            'category': 'invalid',  # not in CATEGORY_CHOICES
            'content': 'test',
        }
        response = self.client.post('/tasklist/listitems/', data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('category', response.data)

    def test_missing_required_fields(self):
        response = self.client.post('/tasklist/listitems/', {})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('title', response.data)
        self.assertIn('content', response.data)


# API tests with APIClient

class TaskAPITest(TestCase):

    def setUp(self):
        self.client = APIClient()
        
        # owner
        self.user = UserFactory(is_staff=True, is_superuser=True)
        
        # other user 
        self.other_user = UserFactory(is_staff=True, is_superuser=False)

        # create a task
        self.task = TodoFactory(owner=self.user)

    # GET - list all tasks
    def test_get_list_authenticated(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get('/tasklist/listitems/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    # GET - unauthenticated should fail
    def test_get_list_unauthenticated(self):
        response = self.client.get('/tasklist/listitems/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    # GET - single task
    def test_get_detail(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(f'/tasklist/listitems/{self.task.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['title'], self.task.title)

    # PATCH - owner can update
    def test_patch_owner(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.patch(
            f'/tasklist/listitems/{self.task.id}/',
            {'title': 'Updated Title'}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['title'], 'Updated Title')

    # PATCH - non-owner cannot update
    def test_patch_non_owner(self):
        self.client.force_authenticate(user=self.other_user)
        response = self.client.patch(
            f'/tasklist/listitems/{self.task.id}/',
            {'title': 'Hacked Title'}
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    # DELETE - owner can delete
    def test_delete_owner(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.delete(f'/tasklist/listitems/{self.task.id}/')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(ListTzuf.objects.count(), 0)

    # DELETE - non-owner cannot delete
    def test_delete_non_owner(self):
        self.client.force_authenticate(user=self.other_user)
        response = self.client.delete(f'/tasklist/listitems/{self.task.id}/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(ListTzuf.objects.count(), 1)  # task still exists
        

    def test_me_returns_correct_user(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get('/tasklist/user/me/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['username'], self.user.username)

    def test_me_unauthenticated(self):
        response = self.client.get('/tasklist/user/me/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_me_returns_own_user_not_other(self):
        self.client.force_authenticate(user=self.other_user)
        response = self.client.get('/tasklist/user/me/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['username'], self.other_user.username)  # not 'owner'
