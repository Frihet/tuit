from django.db import models
from django.contrib.auth.models import User
from tuit.ticket.templatetags.tuit_extras import datetime_format, date_format

# Create your models here.

class Status(models.Model):
    """
    This field represents a status article
    """
    body  = models.TextField(maxlength=65535)
    creation_date = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(User, related_name='status_update')


    def __str__(self):
        return _('Status message by %(source)s made on %(date)s')% {'source':self.user.username,'date':datetime_format(self.creation_date)}

    class Admin:
        pass

    class Meta:
        verbose_name_plural = _('Status messages')
        verbose_name = _('Status message')

    
