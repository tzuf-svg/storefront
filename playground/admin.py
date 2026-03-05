from django.contrib import admin
from .models import ListTzuf, Tag


@admin.register(ListTzuf)
class ListTzufAdmin(admin.ModelAdmin):
    filter_horizontal = ('tags',)
    # עמודות שיופיעו בטבלה הראשית
    list_display = ('title', 'owner', 'completed', 'created_at')
    # אפשרות לערוך את ה-owner בתוך דף העריכה
    fields = ('title', 'content', 'owner', 'completed')
    # הוספת אפשרות סינון לפי בעלים או מצב ביצוע
    list_filter = ('owner', 'completed', 'tags')


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ['name']