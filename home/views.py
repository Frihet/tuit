# Views for the home app of tuit
# -*- coding: utf-8 -*-

from tuit.ticket.models import *
#from django.http import *
from tuit.json import to_json
#import datetime
from django.contrib.auth.models import *
from tuit.util import *
#import re
from django.utils.translation import gettext as _
import logging
from tuit.home.widget import Widget
from tuit.home.models import Tip

@login_required
def home(request):
    """
    Basic home view - show a few status widgets and nothing else. Widget.py does the heavy lifting...
    """
    status_closed = properties["issue_closed_id"]
    if not hasattr(status_closed,'__iter__'):
        status_closed=[status_closed]
    keys={'tip':Tip.current()}
    
    widgets = map(lambda x: Widget(_('My highest priority open tickets of type %s') % x.name,
                                           Issue.objects.exclude(current_status__in = status_closed).filter(assigned_to=request.user).filter(type=x).extra(select={'priority_placeholder':'impact+urgency'}).order_by('-priority_placeholder'),
                                           request, 'my_priority_' + x.name),
                          IssueType.objects.all().order_by('name'))
    widgets.append(Widget(_('Latest open tickets'),
               Issue.objects.exclude(current_status__in = status_closed).order_by('-creation_date'),
               request, 'latest'))

    widgets.append(Widget(_('Oldest unassigned, open tickets'),
               Issue.objects.exclude(current_status__in = status_closed).filter(assigned_to__isnull=True).order_by('creation_date'),
               request,'unassigned_oldest'))

    keys['widgets'] = widgets


#         [
#        Widget(_('My latest open tickets'),
#               Issue.objects.exclude(current_status__in = status_closed).filter(assigned_to=request.user).order_by('creation_date'), 
#               request, 'my_latest'),
#        Widget(_('My oldest open tickets'),
#               Issue.objects.exclude(current_status__in = status_closed).filter(assigned_to=request.user).order_by('-creation_date'),
#               request, 'my_oldest'),
#        Widget(_('My highest priority open tickets'),
#               Issue.objects.exclude(current_status__in = status_closed).filter(assigned_to=request.user).extra(select={'priority_placeholder':'impact+urgency'}).order_by('-priority_placeholder'),
#               request, 'my_priority'),
#        Widget(_('My last updates'),
#               IssueUpdate.objects.order_by('-creation_date').filter(user=request.user).distinct('issu#e_id'), request, 'my_latest_updates', class_names='full_width'),
#        Widget(_('Latest unassigned, open tickets'),
#               Issue.objects.exclude(current_status__in = status_closed).filter(assigned_to__isnull=True).order_by('creation_date'),
#               request,'unassigned_latest'),
#        Widget(_('Highest priority unassigned, open tickets'),
#               Issue.objects.exclude(current_status__in = status_closed).filter(assigned_to__isnull=True).extra(select={'priority_placeholder':'impact+urgency'}).order_by('-priority_placeholder'),
#               request, 'unassigned_priority'),
#        Widget(_('Oldest open tickets'),
#               Issue.objects.exclude(current_status__in = status_closed).order_by('creation_date'),
#               request, 'oldest'),
#        Widget(_('Highest priority open tickets'),
#               Issue.objects.exclude(current_status__in = status_closed).extra(select={'priority_placeholder':'impact+urgency'}).order_by('-priority_placeholder'),
#               request,'priority'),
#        Widget(_('Last updated tickets'),
#               IssueUpdate.objects.order_by('-creation_date'),
#               request,'latest_updates'),
#        ]
    keys['title'] = _("Home")
    return tuit_render('home.html', keys, request)
