from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinLengthValidator


# adding tags to task
class Tag(models.Model):
    name=models.CharField(max_length=25, unique=True)

    def __str__(self):
        return self.name


class ListTzuf(models.Model):
    # categoris of tasks    
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
    coworker = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='tasks')
    completed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    owner = models.ForeignKey('auth.User', related_name='listtzufs', on_delete=models.CASCADE, null=True, default='TzufR')
    completed_at = models.DateTimeField(null=True, blank=True)
    tags = models.ManyToManyField(Tag, related_name="tasks", blank=True)

    def __str__(self):
        return self.title
    

