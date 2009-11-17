from tuit.util import *
from tuit.search.models import *
from django.http import HttpResponse
from django.shortcuts import render_to_response
#from django.contrib.auth.decorators import login_required
from tuit.util import *
from tuit.json import to_json
from tuit.ticket.models import *
from django.utils.translation import gettext as _
from tuit.util import check_permission

@login_required
def results(request):
    vars = {'get':request.GET}
    vars['title'] = _("Search")
    vars['has_advanced']=False
    for it in ('from_date','priority','status'):
        if it in request.GET:
            if it == 'status':
                try:
                    vars[it] = int(request[it])
                except:
                    vars[it] = request[it]
            else:
                vars[it] = request[it]

            vars['has_advanced']=True

    vars['status_all'] = Status.objects.all()

    if 'freetext' in request.GET:
        results = []
        locations = filter(lambda x:check_permission(x.permission,request.user),
                           SearchType.objects.all().order_by('view_order'))
        for typ in locations:
            url = typ.url % ModelDict(request.GET)
            #content = fetch_url(url)
            results.append({'url':url,'id':typ.id})

        vars['results']=to_json(results)

    vars['types'] = SearchType.objects.all().order_by('view_order')
    #vars = request.GET#dict(request.GET)

    return tuit_render('search.html', vars, request)

