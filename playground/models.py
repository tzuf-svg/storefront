from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinLengthValidator
from django.core.exceptions import ValidationError
from datetime import date, timedelta
from django.utils import timezone



# tags to task
class Tag(models.Model):
    name=models.CharField(max_length=25, unique=True)

    def __str__(self):
        return self.name
    
  
# due date
def default_due_date():
    # one week from today, skip weekend
    due = date.today() + timedelta(weeks=1)
    if due.weekday() == 5:   # Saturday → Monday
        due += timedelta(days=2)
    elif due.weekday() == 6:  # Sunday → Monday
        due += timedelta(days=1)
    return due

# not today or in the past
def validate_due_date(value):
    if value <= date.today():
        raise ValidationError("Due date must be in the future.")
    if value.weekday() >= 5:  # 5=Saturday, 6=Sunday
        raise ValidationError("Due date cannot be on a weekend.")


class ListTzuf(models.Model):

    CATEGORY_CHOICES = [
        ('work', 'Work'),
        ('personal', 'Personal'),
        ('urgent', 'Urgent'),
        ('management', 'Management'),
    ]
    
    title = models.CharField(
        max_length=100,
        validators=[MinLengthValidator(3)]
        )
    category = models.CharField(choices=CATEGORY_CHOICES, default='work')
    content = models.TextField()
    coworker = models.ManyToManyField(User, blank=True, related_name='tasks')
    completed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    owner = models.ForeignKey('auth.User', related_name='listtzufs', on_delete=models.CASCADE, null=True, default='TzufR')
    completed_at = models.DateTimeField(null=True, blank=True)
    tags = models.ManyToManyField(Tag, related_name="tasks", blank=True)
    due_date = models.DateField(default=default_due_date, validators=[validate_due_date]
)
    
    def __str__(self):
        return self.title
    
    # saving date completed_at
    def save(self, *args, **kwargs):
        if self.completed and not self.completed_at:
            self.completed_at = timezone.now()
        elif not self.completed:
            self.completed_at = None
        super().save(*args, **kwargs)


class WebhookEvent(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processed', 'Processed'),
        ('failed', 'Failed'),
    ]   
    
    payload = models.JSONField()
    received_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')

