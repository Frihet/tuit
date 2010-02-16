from tuit.ticket.models import *
from django.http import *
import datetime
from django.contrib.auth.models import *
from tuit.util import *
from django.utils.translation import gettext as _
import logging
from tuit.home.widget import Widget

@login_required
def view(request):
    """
    Show current trends in issues. The trensda are based on what CI
    combinations are popular.
    """
    keys = {}

    date_stop = datetime.date.today()
    date_start = date_stop - datetime.timedelta(7)

    try:
        date_stop = datetime.datetime.strptime(request.GET['date_stop'].strip(),properties['date_format'])
        date_start = datetime.datetime.strptime(request.GET['date_start'].strip(),properties['date_format'])
    except:
        #Incorrect date or no date. Ignore...
        pass
    

    items = Issue.objects.filter(creation_date__gte = date_start, creation_date__lte = date_stop)
    def item_key(item):
        """" 
        Create a unique, hashable key for a ci dependency
        queryset. It is a sorted tuple of dependency ids.
        """
        return tuple(map(lambda dep: dep.ci_id, item.cidependency_set.order_by('id')))

    item_pairs = map(lambda item: (item_key(item), item), items)
    
    item_group = {}
    for key, value in item_pairs:
        if key not in item_group:
            item_group[key] = []
        item_group[key].append(value)

    print 'map', item_group
    items = map( lambda (cis, issues): {'ci_list':cis, 
                                       'issue_list':issues, 
                                       'order':len(issues)}, 
                 item_group.iteritems() )
    items = sorted(items, lambda x, y: y['order']-x['order'])
    items = items[:20]

    ci_id = set()
    for i in items:
        print i['ci_list']
        ci_id = ci_id.union(i['ci_list'])

    desc = dict(map(lambda x: (x.ci_id, x.description),CiDependency.objects.filter(ci_id__in = ci_id)))

    for i in items:
        i['ci_desc'] = ", ".join(map(lambda x: desc[x], i['ci_list']))
        if i['ci_desc'] == "":
            i['ci_desc'] = _("None")

    #print 'AAAAA', desc
    # Fetch ci descriptions

 #   print 'items', items
    
    keys['date_start'] = date_start
    keys['date_stop'] = date_stop
    keys['trend_data'] = items

    return tuit_render('trend.html', keys, request)



