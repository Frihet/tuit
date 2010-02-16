from django.db import models

# Create your models here.

PLACEHOLDER=_('Components')

class Component(models.Model):
    alias = models.CharField(maxlength=64)
    name = models.CharField(maxlength=512)
    url = models.CharField(maxlength=512)
    permission = models.CharField(maxlength=64,blank=True)
    view_order = models.IntegerField()

    def __str__(self):
        return self.name

    class Admin: 
        pass

    class Meta:
        ordering = ['name']
        verbose_name_plural = _('Menu components')
        verbose_name = _('Menu component')


PLACEHOLDER=_('Menu')

