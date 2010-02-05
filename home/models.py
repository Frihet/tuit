# Models for the home app of tuit
# -*- coding: utf-8 -*-

from django.db import models
from django.utils.translation import gettext as _
import datetime

# Here begins the list of models proper

class Tip(models.Model):
    """
    Tip of the week
    """

    title = models.CharField(maxlength=128)
    body = models.TextField(maxlength=4096)
    display_date = models.DateField()

    def __str__(self):
        return str(self.display_date) + " - " +self.title

    class Admin: 
        pass

    class Meta:
        ordering = ['display_date']
        verbose_name_plural = _('Tips')
        verbose_name = _('Tip of the week')

    @staticmethod
    def current():
        try:
            return Tip.objects.filter(display_date__lte = datetime.date.today()).order_by('-display_date')[0]
        except:
            import traceback as tb
            tb.print_exc()
            return None

