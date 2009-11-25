# Create your views here.

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


@login_required
def home(request):
    status_open = Status.objects.get(name='Open')
    status_closed = Status.objects.get(name='Closed')
    keys={}



    keys['widgets'] = map(lambda x: Widget(_('My highest priority open tickets of type %s') % x.name,
                                           Issue.objects.exclude(current_status = status_closed).filter(assigned_to=request.user).filter(type=x).extra(select={'priority_placeholder':'impact+urgency'}).order_by('-priority_placeholder'),
                                           request, 'my_priority'),
                          IssueType.objects.all().order_by('name'))

#         [
#        Widget(_('My latest open tickets'),
#               Issue.objects.exclude(current_status = status_closed).filter(assigned_to=request.user).order_by('creation_date'), 
#               request, 'my_latest'),
#        Widget(_('My oldest open tickets'),
#               Issue.objects.exclude(current_status = status_closed).filter(assigned_to=request.user).order_by('-creation_date'),
#               request, 'my_oldest'),
#        Widget(_('My highest priority open tickets'),
#               Issue.objects.exclude(current_status = status_closed).filter(assigned_to=request.user).extra(select={'priority_placeholder':'impact+urgency'}).order_by('-priority_placeholder'),
#               request, 'my_priority'),
#        Widget(_('My last updates'),
#               IssueUpdate.objects.order_by('-creation_date').filter(user=request.user).distinct('issu#e_id'), request, 'my_latest_updates', class_names='full_width'),
#        Widget(_('Latest unassigned, open tickets'),
#               Issue.objects.exclude(current_status = status_closed).filter(assigned_to__isnull=True).order_by('creation_date'),
#               request,'unassigned_latest'),
#        Widget(_('Oldest unassigned, open tickets'),
#               Issue.objects.exclude(current_status = status_closed).filter(assigned_to__isnull=True).order_by('-creation_date'),
#               request,'unassigned_oldest'),
#        Widget(_('Highest priority unassigned, open tickets'),
#               Issue.objects.exclude(current_status = status_closed).filter(assigned_to__isnull=True).extra(select={'priority_placeholder':'impact+urgency'}).order_by('-priority_placeholder'),
#               request, 'unassigned_priority'),
#        Widget(_('Latest open tickets'),
#               Issue.objects.exclude(current_status = status_closed).order_by('-creation_date'),
#               request, 'latest'),
#        Widget(_('Oldest open tickets'),
#               Issue.objects.exclude(current_status = status_closed).order_by('creation_date'),
#               request, 'oldest'),
#        Widget(_('Highest priority open tickets'),
#               Issue.objects.exclude(current_status = status_closed).extra(select={'priority_placeholder':'impact+urgency'}).order_by('-priority_placeholder'),
#               request,'priority'),
#        Widget(_('Last updated tickets'),
#               IssueUpdate.objects.order_by('-creation_date'),
#               request,'latest_updates'),
#        ]
    keys['title'] = _("Home")
    return tuit_render('home.html', keys, request)
