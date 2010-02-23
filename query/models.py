from django.db import models
from django.contrib.auth.models import User, Group
from tuit.ticket.models import IssueField

# Create your models here.

PLACEHOLDER=_('Query')

class GenericFillItem(models.Model):
    field = models.ForeignKey(IssueField)
    value = models.CharField(maxlength=32000)
    condition_name = models.ForeignKey(IssueField, related_name = 'trigged_by')
    condition_value = models.CharField(maxlength=64)

    def __str__(self):
        return self.condition_name.name + ": " + self.condition_value + " -> " + str(self.field) + ": " + str(self.value)
    
    def __to_json__(self):
        return {
            '__jsonclass__':['GenericFillItem', self.id],
            'field':self.field.name,
            'value':self.value}

    class Admin: 
#        list_filter = ('condition_name',)
        pass

    class Meta:
#        ordering = ['condition_name']
        verbose_name_plural = _('Generic fill items')
        verbose_name = _('Generic fill item')


