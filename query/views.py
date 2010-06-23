# Create your views here.

from tuit.util import *
from django.http import HttpResponse
from django.contrib.auth.models import *
from tuit.json import to_json
from django.db.models.query import Q, QOr, QAnd
from tuit.ticket.models import *
import datetime
import re
from tuit.query.models import *

class QLeftOuterJoins(Q):
    """
    Replaces all INNER JOINs with LEFT OUTER JOINs inside

    This code from DjangoSnippets, 

    http://www.djangosnippets.org/snippets/274/

    Without it, any issues without updates would fail, which is bad.
    """
    def __init__(self, q):
        self.q = q

    def __and__(self, other):
        return QAnd(self, other)

    def __or__(self, other):
        return QOr(self, other)

    def get_sql(self, opts):
        joins, where, params = self.q.get_sql(opts)
        for join_name, join in joins.iteritems():
            joins[join_name] = (join[0], "LEFT OUTER JOIN", join[2])
        return joins, where, params

# Go over all the words in the search, filter on all of them
def make_Q(query, fld):
    q=None
    
    sub_q = query.split(' ')

    if (len(sub_q)==1) or sub_q[1] == '-':
        try:
            num = int(sub_q[0])
            kw={'id__exact': num,}
            return QLeftOuterJoins(Q(**kw))
        except:
            pass

    for i in sub_q:
        if i=='-':
            continue
        nq = None
        for f in fld:
            kw={f+'__icontains': i,}
            print 'tjoho', kw
            nq2 = Q(**kw)
            if nq:
                nq = nq | nq2
            else:
                nq=nq2
        if q:
            q = q & nq
        else:
            q=nq
    return QLeftOuterJoins(q)

@login_required
def user_complete(request):
    query = request.GET['query']
    q = make_Q(query, ('username','first_name','last_name','email',))
    q = User.objects.filter(q).order_by('username')

    if 'search' in request.GET:
        u = {'ResultSet':{'totalResultsAvailable':len(q),
                          'totalResultsReturned':len(q),
                          'firstResultPosition':0,
                          'Result':map(lambda user: {'name': "%s - %s %s" % (user.username, user.first_name, user.last_name),
                                                     'description':'hejsan',
                                                     'url':'/tuit/account/%s'%escape_recursive(user.username)}, q)
                          }
             }
    else:
        u = map(lambda user: "%s - %s %s" % (user.username, user.first_name, user.last_name), q)
        if 'contacts' in request.GET:
            q2 = make_Q(query, ('name','email',))
            q2 = Contact.objects.filter(q2).order_by('name')
            u2 = map(lambda user: user.format, q2)
            u.extend(u2)

    return HttpResponse(to_json(u))

@login_required
def autofill(request):
    """
    Returns the location data for the specified username as a json dict.
    """
    try:
        field = request.GET['field']
        if field == 'requester':
            username = request.GET['value']
            p = User.objects.get(username=username).get_profile()
            res=p.__dict__
        else:
            value = request.GET['value']
            val_arr = value.split(' ')
            if len(val_arr) > 2 and val_arr[1] == '-':
                value= val_arr[0]
            print 'f,d', field, value
            data = GenericFillItem.objects.filter(condition_name__name = field, condition_value = value)
            res = list(data)
        return HttpResponse(to_json(res))
    except:
        raise
#        return HttpResponse("{}")

@login_required
def issue_complete(request):
    """
    Used for autocompleting issues and for searching for issues. Uses
    text format for autocompletion, and the json based Yahoo search
    format for searches.
    """
    query = request.GET['query']
    offset = 0
    if 'offset' in request.GET:
        offset = int(request.GET['offset'])
        
    q = make_Q(query, ('subject','description','issueupdate__comment','requester__username','requester__first_name','requester__last_name'))
    q = Issue.objects.filter(q)
    if not request.user.is_staff:
        q = q.filter(requester=request.user)

    if 'status' in request.GET and request.GET['status'] != '':
        try:
            status = request.GET['status']

            if status == 'all':
                # No filtering!
                pass
            else:
                q=q.filter(current_status = int(status))
            
        except:
            #Incorrect status. Ignore...
            pass
    else:
        # Default: show only non-open tickets
        status_closed = properties['issue_closed_id']
        if not hasattr(status_closed,'__iter__'):
            status_closed=[status_closed]
        q=q.exclude(current_status__in = status_closed)

    q = q.distinct().order_by('-creation_date')
    # This will fetch the items into a list that we can use map on...
    q=q[:]

    # FIXME: This filter can be moved to the database for higher speed
    if 'from_date' in request.GET:
        try:
            from_date = request.GET['from_date'].strip()
            from_date = datetime.datetime.strptime(from_date,properties['date_format'])
            q = filter(lambda x:x.last_update_date > from_date, q)
        except:
            #Incorrect date. Ignore...
            pass

        
    # FIXME: This filter is pretty tricky to move to the database,
    # because priority is not a field, it is the sum of two other
    # fields, but it should be possible to use extra_fields to make it
    # work.
    if 'priority' in request.GET and request.GET['priority'] != '':
        try:
            prios = re.match(r'^ *([0-9]+) *(\.\. *([0-9]+)|) *$', request.GET['priority']).groups()
            if prios[2] is None:
                prio = int(prios[0])
                q = filter(lambda x:x.priority == prio, q)                
            else:
                prio_min = int(prios[0])
                prio_max = int(prios[2])
                q = filter(lambda x:x.priority >= prio_min and x.priority <=prio_max, q)               
        except:
            #Incorrect priority. Ignore...
            pass

    if 'search' in request.GET:
        tot_count = len(q)
#        q = q[offset:min(len(q),offset+100)]
 
        u = {'ResultSet':{'totalResultsAvailable':tot_count,
                          'totalResultsReturned':len(q),
                          'firstResultPosition':offset,
                          'Result':map(lambda issue: {'name':issue.subject,'description':'hejsan','url':'/tuit/ticket/view/%d'%issue.id}, q)
             }}
    else:
        u = map(lambda issue: "%s - %s" % (issue.id, issue.subject), q)
    return HttpResponse(to_json(u))

