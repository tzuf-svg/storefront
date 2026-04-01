import logging
from django.dispatch import receiver
from allauth.socialaccount.signals import social_account_removed

logger = logging.getLogger(__name__)


@receiver(social_account_removed)
def handle_social_account_removed(request, socialaccount, **kwargs):
    user = socialaccount.user
    logger.info(f"The user {user.username} has logged out")