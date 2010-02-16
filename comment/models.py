from django.db import models
from django.contrib.auth.models import User
from tuit.ticket.templatetags.tuit_extras import date_format, datetime_format

# Create your models here.
class Comment(models.Model):
    """
    Comment about a tuit page
    """
    text = models.TextField(maxlength=4096)
    user = models.ForeignKey(User, related_name='comment')
    creation_date = models.DateTimeField(auto_now_add=True)
    url = models.CharField(maxlength=1024, db_index=True)

    def __str__(self):
        return self.url

    @property
    def dict(self):
        return {
            'text':self.text, 
            'creation_time':datetime_format(self.creation_date),
            'username':self.user.username,
            'name':self.user.name,
            }
    

    class Admin: 
        list_display = ('url','text')
        search_fields=('text','url')
        list_filter = ('url',)

    class Meta:
        ordering = ['creation_date']
        verbose_name_plural = _('Comments')
        verbose_name = _('Comment')
