import pytest
from django.test import Client as DjangoClient
from rest_framework.test import APIClient


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def django_client():
    return DjangoClient()
