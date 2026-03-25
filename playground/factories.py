import factory
from django.contrib.auth.models import User
from factory.django import DjangoModelFactory
from datetime import date, timedelta
from .models import ListTzuf, WebhookEvent, default_due_date


class UserFactory(DjangoModelFactory):
    class Meta:
        model = User
        django_get_or_create = ('username',)

    username = factory.Sequence(lambda n: f'user{n}')
    is_staff = False
    is_superuser = False

    class Params:
        staff = factory.Trait(is_staff=True)
        superuser = factory.Trait(is_staff=True, is_superuser=True)


class TodoFactory(DjangoModelFactory):
    class Meta:
        model = ListTzuf

    title = factory.Faker('sentence', nb_words=4)
    category = 'work'
    content = factory.Faker('paragraph')
    owner = factory.SubFactory(UserFactory)
    completed = False
    due_date = factory.LazyFunction(default_due_date)

    class Params:
        urgent = factory.Trait(category='urgent')
        management = factory.Trait(category='management')


class WebhookEventFactory(DjangoModelFactory):
    class Meta:
        model = WebhookEvent

    payload = factory.LazyFunction(lambda: {'event': 'test'})
    status = 'pending'
