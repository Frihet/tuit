# Create your views here.
# -*- coding: utf-8 -*-

from tuit.ticket.models import *
from django.http import *
from tuit.json import to_json
import datetime
from django.contrib.auth.models import *
from tuit.util import *
import re
from django.utils.translation import gettext as _
import logging

def studly(str):
    return "".join(map(lambda x:x.capitalize(),re.sub(r'[^a-zA-Z0-9_ åæøäö]', '', str).split(" ")))


def insert_view_data(keys, request, default_checked_list):
    default_checked = set(map(lambda x: x + '_email',default_checked_list))
    i = keys['issue']
    keys['status'] = Status.objects.all()
    keys['category'] = Category.objects.all()
    keys['impacts'] = map(lambda x:str(x),range(1,6))
    keys['urgencies'] = map(lambda x:str(x),range(1,6))
    keys['types'] = IssueType.objects.all().order_by('name')
    for box in ('update_dependants','internal','assigned_to_email','requester_email','co_responsible_email','cc_email'):
        if request.method=='POST':
            if box in request.POST:
                keys[box]='checked'
        elif box in default_checked:
            keys[box]='checked'





def format_errors(errors):
    res = ""
    for key, val in errors.iteritems():
        for msg in val:
            res += "<div class='error'>%s: %s</div>" % (key, msg)
    return res

@login_required
def new(request, type_name=None):
    print request.user
    keys = request.POST.copy()
    keys['quick_fill'] = QuickFill.objects.all()
    keys['quick_fill_json'] = to_json(QuickFill.objects.all())
    keys['status'] = Status.objects.all()
    keys['errors'] = {}
    keys['messages'] = ""

    if type_name is None:
        type_name=request.GET['type']
    type = IssueType.objects.get(name=type_name)
    keys['type'] = type
    keys['ticket_new'] = True

    keys['title'] = _('New %s') % type.name
    i = Issue()
    i.creator = request.user

    if request.method == 'POST': # If the form has been submitted...

        # We can't save more than half of the issue before getting an id for the line, so we do it in two phases
        
        # Phase 1
        i.type = IssueType.objects.get(id=request.POST['type'])
        events = i.apply_post(keys)

        i.create_description = '[]'
        errors = i.validate()
        if not errors:
            i.save()

            # Phase 2
            events.extend(i.apply_post(keys))

            for el in ('subject', 'description'):
                setattr(i,el,request.POST[el])

            errors = i.validate()
        
            if not errors:
                events.extend(send_email('web_create', request.POST, i, None))
                i.description_data={'type':'web','events':events, 'by':request.user.username}

                Event.fire(['web_create','create'], i)
                i.save()
                return HttpResponseRedirect('/tuit/ticket/view/%d' % i.id) # Redirect after successfull POST

        logging.getLogger('ticket').error('Tried to create issue, but got the following errors: %s' % str(errors));
        keys['errors'] = errors
        keys['messages'] += format_errors(errors)

        i=ModelWrapper(i, request.POST)
    else:
        i.type = IssueType.objects.get(name=request.GET['type'])
        i.current_status = Status.objects.get(id=properties['issue_default_status'])
        if 'copy' in request.GET:
            template = Issue.objects.get(id=int(request.GET['copy']))
            wrap_dict={}
            for it in ('subject','description','category','impact_string','urgency_string','requester_string','assigned_to_string','cc_string','co_responsible_string'):
                wrap_dict[it] =getattr(template, it)
            i=ModelWrapper(i, wrap_dict)

    keys['create_default_mail_json'] = to_json(properties['web_create_default_mail'])

    keys['issue'] = i
    insert_view_data(keys, request, properties['web_create_default_mail'])
    return tuit_render('ticket_new.html', keys, request)

def update_dependants(issue, update, send_to, ignore):
    for i in issue.dependants.all():
        if i in ignore:
            continue
        ignore.add(i)
        i.current_status = issue.current_status
        iu = IssueUpdate(issue=i,
                         internal = update.internal,
                         comment = update.comment,
                         user=update.user)
        events = send_email('web_update', send_to, i, iu)
        i.save()
        iu.description_data={'type':'web','events':events}
        iu.save()
        update_dependants(i, iu, send_to, ignore)


@login_required
def view(request,id=None):
    if id is None:
        id = request.GET['id']
    i=Issue.objects.get(id=id)
    keys = request.POST.copy()
    keys['messages'] = ""
    keys['update']=None
    keys['show_internal'] = request.user.has_perm('issue.view_internal')

    if request.method == 'POST': # If the form has been submitted...
        events = i.apply_post(request.POST)

        iu = IssueUpdate(issue=i, 
                         internal = 'internal' in request.POST,
                         comment=request.POST['comment'],
                         user=request.user,
                         description_data={})
        errors = i.validate()
        print errors
        
        for name, value_list in iu.validate().iteritems():
            if name in errors:
                errors[name].extend(value_list)
            else:
                errors[name]=value_list

        if not errors:

            events.extend(send_email('web_update', request.POST, i, iu))
                               
            iu.description_data={'type':'web','events':events,'by':request.user.username}

            Event.fire(['web_update','update'], i, iu)
            i.save()
            iu.save()
            if 'update_dependants' in request.POST:
                update_dependants(i, iu, request.POST, set())

            return HttpResponseRedirect('/tuit/ticket/view/%d' % i.id) # Redirect after successfull POST
        logging.getLogger('ticket').error('Tried to create issue update, but got the following errors: %s' % str(errors));
        keys['errors'] = errors
        keys['update']=iu

        keys['messages'] += format_errors(errors)

    keys['internal_default_mail_json'] = to_json(properties['web_internal_default_mail'])
    keys['external_default_mail_json'] = to_json(properties['web_external_default_mail'])

    keys['title'] = _('Viewing %(issue_type)s "%(subject)s"')% {'issue_type':i.type.name, 'subject':i.subject}
    keys['issue'] = i
    keys['kb_name'] = studly(i.subject)
    insert_view_data(keys, request, properties['web_external_default_mail'])
    return tuit_render('ticket_view.html', keys, request)
    



def send_email(template_name, post, issue, update=None):
    events=[]
    e=EmailTemplate.objects.filter(name=template_name)
#    print('We have %d templates of specified type' % len(e)) 
    if len(e) > 0:
        e=e[0]
        for contact in ['assigned_to','requester','co_responsible','cc']:
            var = contact + '_email'
            if var in post:
                events.extend(e.send(getattr(issue, contact), issue=issue, update=update))
                
    else:
        logging.getLogger('ticket').error('No email template of type %s could be found' % template_name)
    return events


@login_required
def attachment(request, id):
    a = IssueUpdateAttachment.objects.get(id=id)
    res = HttpResponse(mimetype=a.mime)
    f = open(a.filename,'r')
    try:
        res.write(f.read())
    finally:
        f.close()
    return res


# Login not required on purpose - we might in the future wish to use
# Norwegian in javascript for the login page.  There is nothing secret
# on this page.
from django.views.decorators.cache import cache_control
@cache_control(max_age=3600*24*7)
def i18n(request):
    trans={'$.dpText.TEXT_CHOOSE_DATE': _('Choose date'),
           '$.dpText.TEXT_PREV_MONTH': _('Previous month'),
           '$.dpText.TEXT_PREV_YEAR': _('Previous year'),
           '$.dpText.TEXT_NEXT_MONTH': _('Next month'),
           '$.dpText.TEXT_NEXT_YEAR': _('Next year'),
           '$.dpText.TEXT_CLOSE': _('Close'),
           'Date.dayNames': [_('Sunday'),_('Monday'),_('Tuesday'),_('Wednesday'),_('Thursday'),_('Friday'),_('Saturday'),],
           'Date.monthNames': [_('January'), _('February'), _('March'), _('April'), _('May'), _('June'), _('July'), _('August'), _('September'), _('October'), _('November'), _('December')]
           }
#    trans_json = dict(map(lambda (x,y): (x, to_json(y)), trans.iteritems()))
    return tuit_render('i18n.js', {'strings':trans}, request)
    
