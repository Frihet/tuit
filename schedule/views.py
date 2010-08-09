# Create your views here.

from tuit.util import *
#from django.http import HttpResponse
#from django.contrib.auth.models import *
#from tuit.json import to_json
#from django.db.models.query import Q, QOr, QAnd
from tuit.ticket.models import *
import datetime
import re
#from tuit.query.models import *


@login_required
def view(request):
    required_field_id = int(request.GET["for"])
    required_field = IssueField.objects.get(id=required_field_id)
    
    possible = map(lambda x: x.issue_id, IssueFieldValue.objects.filter(field = required_field_id))
    issues = Issue.objects.filter(id__in = possible)


    idx = 1
    while True:
        cond_type_k = "condition_type_%d" % idx
        cond_k = "condition_%d" % idx
        if cond_type_k not in request.GET:
            break 
        cond_type = request.GET[cond_type_k]
        print 'cond type:', cond_type

        idx+=1

    schedule = {}
    for i in issues:
        day_str = getattr(i, required_field.name)
        day = date_valid(day_str)
        if day:
            if day not in schedule:
                schedule[day]=[]
            schedule[day].append(i)
    schedule = map(lambda (x,y): {'date':x, 'issues':y}, schedule.iteritems())

    print schedule
    keys = {'schedule': schedule}
    return tuit_render('schedule.html', keys, request)

