# Create your views here.

from tuit.menu.models import *
from django.http import HttpResponse
from django.shortcuts import render_to_response
from tuit.menu.models import *

def check_permission(perm, user):
    if perm == '':
        return True
    if perm == 'is_staff':
        return user.is_staff
    return user.has_perm(perm)

def menu(request):
    components = []
    if request.user.is_authenticated():
        components = filter(lambda x:check_permission(x.permission,request.user),Component.objects.all().order_by('view_order'))
    return render_to_response('menu.html', {'applications':components})

