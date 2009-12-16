# Views for the account app of tuit
# -*- coding: utf-8 -*-
import django.contrib.auth 
from django.http import *

from tuit.ticket.models import *
from tuit.util import *
from django.utils.translation import gettext as _
from tuit.home.widget import Widget
from django.contrib.auth.models import *
from tuit.json import to_json

# Imports for login view
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import REDIRECT_FIELD_NAME
from django import oldforms
from django.contrib.sites.models import Site
from django.template import RequestContext

import logging

def format_requst_info(request):
    """
    Create a html text message describing w bit about what we know
    about a specific http request. Used for logging.
    """
    return "(" + "<br/>\n".join(map(lambda x: "%s: %s"%(x[0],request.META[x[1]]),
                         filter(lambda x: x[1] in request.META,
                                (('IP','REMOTE_ADDR'),
                                 ('User agent','HTTP_USER_AGENT'),
                                 ('Forwarded from','HTTP_X_FORWARDED_FOR'))
                                )
                               )
                           )+ ")"
                               

    

def logout(request):
    logging.getLogger('account').info('User %s logged out %s' % (request.user.username, format_requst_info(request)))
    django.contrib.auth.logout(request)
    return HttpResponseRedirect('/tuit/account/login') 

@login_required
def show(request, id=None, name=None):
    """
    Show information about the specified user. Kind of like the home
    page (lots of code reuse going on between the two), but for any
    user.
    """
    if id:
        user = User.objects.get(id=id)
    elif name:
        user = User.objects.get(username=name)
    else:
        return None
    keys={}
    status_closed=properties["issue_closed_id"]
    if not hasattr(status_closed,'__iter__'):
        status_closed=[status_closed]

    keys['home_user'] = user
    last_updates = IssueUpdate.objects.order_by('-creation_date').filter(user=user).distinct('issue_id')
    if not request.user.has_perm('issue.view_internal'):
        last_updates = last_updates.filter(internal = False)

    keys['widgets'] = [
        Widget(_('All issues requested by this user'),
               Issue.objects.filter(requester=user).order_by('creation_date'),
               request,
               'requested'),
        Widget(_('Open issues assigned to this user'),
               Issue.objects.exclude(current_status__in = status_closed).filter(assigned_to=user).order_by('creation_date'),
               request,
               'owned'),
        Widget(_('This users last updates'),
               last_updates, request, 'updates',class_names='full_width'),
        ]
    
    keys['title'] = "Details for user %s" % user.username

    return tuit_render('account_show.html', keys, request)

# Rewrote the django login, since default redirect was hardcoded in
# and we don't have fullcontrol over urls. :-(
def login(request, template_name='registration/login.html'):
    "Displays the login form and handles the login action."
    manipulator = AuthenticationForm(request)
    redirect_to = request.REQUEST.get(REDIRECT_FIELD_NAME, '')
    if request.POST:
        errors = manipulator.get_validation_errors(request.POST)
        if not errors:
            logging.getLogger('account').info('User %s logged in %s' % (request.POST['username'], format_requst_info(request)))

            # Light security check -- make sure redirect_to isn't garbage.
            if not redirect_to or '://' in redirect_to or ' ' in redirect_to:
                redirect_to = '/tuit/'
            from django.contrib.auth import login
            login(request, manipulator.get_user())
            request.session.delete_test_cookie()
            return HttpResponseRedirect(redirect_to)
    else:
        errors = {}
    request.session.set_test_cookie()
    return render_to_response(template_name, {
        'form': oldforms.FormWrapper(manipulator, request.POST, errors),
        REDIRECT_FIELD_NAME: redirect_to,
        'site_name': Site.objects.get_current().name,
    }, context_instance=RequestContext(request))

def session(request):
    """
    Returns a json object containing session information. 
    
    Fixme: Should we also include e.g. login time?
    """
    res = "null"
    if request.user.is_authenticated():
        res = to_json({'username':request.user.username,
                       'first_name':request.user.first_name,
                       'last_name':request.user.last_name,
                       'email':request.user.email,
                       'groups':map(lambda x:x.name, request.user.groups.all())
                       })

    return HttpResponse(res)
    
