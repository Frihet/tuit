# Models for the home app of tuit
# -*- coding: utf-8 -*-

from django.db import models
from django.utils.translation import gettext as _
import datetime
from tuit.util import *
from tuit.home.widget import Widget
from tuit.ticket.models import Issue


# Here begins the list of models proper

PLACEHOLDER = (_('Tip'),_('Widget'))

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


class DashboardWidget(models.Model):
    """
    Additional home page widgets
    """

    code = models.TextField(maxlength=819200)
    view_order = models.IntegerField(_('view order'))
    permission = models.CharField(_('permission'),maxlength=64,blank=True)

    def __str__(self):
        return "Widget number %d, with permission %s" % (self.view_order, self.permission)

    class Admin: 
        pass

    class Meta:
        ordering = ['view_order']
        verbose_name_plural = _('Dashboard Widgets')
        verbose_name = _('Dashboard Widget')

    def render(self, request):
        if not check_permission(self.permission, request.user):
            return ""
        result=[]
        user=request.user
        try:
            exec self.code.replace('\r','')
        except:
            print self.code
            import traceback as tb
            tb.print_exc()
            return []
        return result

        
