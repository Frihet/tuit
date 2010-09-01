# Create your views here.
from tuit.ticket.models import *
from django.http import *
#from tuit.json import to_json
import datetime
from django.contrib.auth.models import *
from tuit.util import *
#import re
import django.contrib.auth.models
from django.utils.translation import gettext as _
from django.utils.translation import gettext_noop
import logging
from tuit.query.models import GenericFillItem
import traceback
from tuit.home.widget import Widget

@login_required
def view(request):
    keys = {}
    user=request.user
    status_closed = properties["issue_closed_id"]
    w = Widget('My requests', Issue.objects.filter(requester=user).exclude(current_status__in = status_closed).order_by('creation_date'), request, 'new')
    keys['widget'] = w
    keys['user'] = user
    keys['issue_default_status'] = properties['issue_default_status']
    keys['types'] = IssueType.objects.all().order_by('name')
    i = Issue()
    i.type = IssueType.objects.all()[0]
    keys['issue'] = i
    return tuit_render("elkjop_simple.html", keys, request)
