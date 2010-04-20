from django.db import models

# Create your models here.

PLACEHOLDER=_('Components')

class Component(models.Model):
    alias = models.CharField(_('alias'),maxlength=64)
    name = models.CharField(_('name'),maxlength=512)
    url = models.CharField(_('url'),maxlength=512)
    permission = models.CharField(_('permission'),maxlength=64,blank=True)
    view_order = models.IntegerField(_('view order'),)

    def __str__(self):
        return self.name

    class Admin: 
        pass

    class Meta:
        ordering = ['name']
        verbose_name_plural = _('Menu components')
        verbose_name = _('Menu component')


PLACEHOLDER=_('Menu')

