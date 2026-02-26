from django.db import models
from django.contrib.auth.models import User




class ListTzuf(models.Model):
    # categoris of tasks    
    CATEGORY_CHOICES = [
        ('work', 'Work'),
        ('personal', 'Personal'),
        ('urgent', 'Urgent'),
        ('management', 'Management'),
    ]
    
    title = models.CharField(max_length=100)
    category = models.CharField(choices=CATEGORY_CHOICES, default='work')
    content = models.TextField()
    completed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    owner = models.ForeignKey('auth.User', related_name='listtzufs', on_delete=models.CASCADE, null=True, default='TzufR')
    completed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.title
    

