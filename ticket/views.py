# Views for the ticket app of tuit
# -*- coding: utf-8 -*-

from tuit.ticket.models import *
from django.http import *
from tuit.json import to_json
import datetime
from django.contrib.auth.models import *
from tuit.util import *
import re
import django.contrib.auth.models
from django.utils.translation import gettext as _
from django.utils.translation import gettext_noop
import logging
from tuit.query.models import GenericFillItem
import traceback
import tuit.home.widget

def studly(str):
    """
    Converts a sentence into a StudlyCaps word.
    """
    return "".join(map(lambda x:x.capitalize(),re.sub(r'[^a-zA-Z0-9_ åæøäö]', '', str).split(" ")))

def insert_view_data(keys, request, default_checked_list):
    """
    Inserts common data to all types of query views into the dict.

    This includes data about default checkboxes, a list of available
    categories, statuses, urgencies and impacts and various other
    data.
    """
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

def handle_files( issue, update, files ):
    res=[]
    print 'TRY HANDLING FILES!!!'
#    print files
    idx = 0
    for filename in files:
        print 'handle a file...'
        file = files[filename]
#        print file
#        IssueAttachment.create(issue, update, file.read(), file.name, file.content_type)
        IssueAttachment.create(issue, update, file['content'], file['filename'], file['content-type'], idx)
        idx += 1
        print 'ok'
    print 'DONE AND DONE!!!'
    return res


def format_errors(errors):
    """
    Turns a django-stykle list of validation errors into a html status
    message text.
    """
    res = ""
    for key, val in errors.iteritems():
        for msg in val:
            res += "<div class='error'>%s: %s</div>" % (key, msg)
    return res

@login_required
def new(request, type_name=None):
    """
    View for creating a new ticket
    """
    
    # Do a copy to get a real dict, not a weird django-style query-dict
    # with their pseudo-list interface.
    keys = request.POST.copy()
    
    keys['quick_fill'] = QuickFill.objects.all()
    keys['quick_fill_json'] = to_json(QuickFill.objects.all())
    
    keys['field_fill_json'] = to_json(set(map(lambda x: x.condition_name.name, GenericFillItem.objects.filter())))
    
    keys['status'] = Status.objects.all()
    keys['errors'] = {}
    keys['messages'] = ""
    
    type = None
    if type_name is None and 'type' in request.GET:
        type_name=request.GET['type']
    if not type_name is None:
        type = IssueType.objects.get(name=type_name)
    elif 'type_id' in request.GET:
        type = IssueType.objects.get(id=int(request.GET['type_id']))

    if not type is None:
        keys['title'] = _('New %s') % type.name    
        keys['type'] = type
    else:
        keys['title'] = _('New issue')

    keys['ticket_new'] = True
    
    
    i = Issue()
    i.creator = request.user
    
    if request.method == 'POST': 
        # If the form has been submitted...
        # We can't save more than half of the issue before getting an id for the line, so we do it in two phases
        
        # Phase 1
        i.type = IssueType.objects.get(id=request.POST['type_id'])
        events = i.apply_post(keys)

        i.create_description = '[]'

        errors = i.validate()
        # FIXME: Ugly hack to get field names trasnslated in error
        # messages. Drop when we have fully dynamic forms in R2.
        name_lookup = dict(map(lambda i:(i.name, i.short_description),IssueField.objects.all()))
        print name_lookup
        formated_errors = {}
        for key, value in errors.iteritems():
            if key in name_lookup:
                formated_errors[name_lookup[key]] = value
            elif key + "_string" in name_lookup:
                formated_errors[name_lookup[key+"_string"]] = value
            else:
                formated_errors[key] = value
        errors = formated_errors
        if not errors:
            i.save()

            # Phase 2
            events.extend(i.apply_post(keys))

            for el in ('subject', 'description'):
                setattr(i,el,request.POST[el])

            errors = i.validate()
        
            print 'BAZ', errors
            if not errors:
                events.extend(handle_files(i, None, request.FILES, request.POST))
                events.extend(send_email('web_create', request.POST, i, None))

                i.description_data={'type':'web','events':events, 'by':request.user.username}
                
                # Fire of event handler
                Event.fire(['web_create','create'], i)
                i.save()
                
                # If everything went ok with form submission, this is where we return
                logging.getLogger('ticket').info('Created issue with id %d' % i.id)

                url = '/tuit/ticket/view/%d' % i.id 
                if 'continue' in request.POST:
                    url = '/tuit/ticket/new/?type=' + cgi.escape(i.type.name)
    
                return HttpResponseRedirect(url)

        # This code is only reached oif we get an error while processing the form
        logging.getLogger('ticket').error('Tried to create issue, but got the following errors: %s' % str(errors));
        keys['errors'] = errors
        keys['messages'] += format_errors(errors)

        i=ModelWrapper(i, request.POST)
    else:
        # This is not a form submission, show an empty form
        if not type is None:
            i.type = type
        i.current_status = Status.objects.get(id=properties['issue_default_status'])
        # But wait! It should not be empty, it should be a copy of an already existing ticket
        if 'copy' in request.GET:
            template = Issue.objects.get(id=int(request.GET['copy']))
            wrap_dict={}
            for it in ('subject','description','category','impact_string','urgency_string','requester_string','assigned_to_string','cc_string','co_responsible_string'):
                wrap_dict[it] =getattr(template, it)
            i=ModelWrapper(i, wrap_dict)
        else:
            for mail_checkbox in properties['web_create_default_mail']:
                keys[mail_checkbox + "_email"] = "yes"

    keys['types'] = IssueType.objects.all()
    keys['issue'] = i
    keys['issue_default_type'] = properties['issue_default_type']
    insert_view_data(keys, request, properties['web_create_default_mail'])
    template = 'ticket_new.html'
    if 'partial' in request.GET:
        template = 'ticket_new_form.html'
    return tuit_render(template, keys, request)

def update_dependants(issue, update, send_to, ignore):
    """
    An issue with other issues depending on it has been updated, and
    the «update dependants» box has been checked.

    Update all dependant tickets as well, and send emails to the
    relevant people.
    """
    for i in issue.dependants.all():
        if i in ignore:
            continue
        ignore.add(i)
        i.current_status = issue.current_status
        i.ci_string = issue.ci_string
        
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
    """
    This is the main issue viewing view. It shows an issue, and
    provides the option to send an issue update as well.
    """
    if id is None:
        id = request.GET['id']
    try:
        i=Issue.objects.get(id=id)
    except:
        return tuit_render('ticket_view.html', {}, request)


    keys = request.POST.copy()
    keys['messages'] = ""
    keys['update']=None
    keys['show_internal'] = request.user.has_perm('ticket.view_internal')

    if request.method == 'POST': 
        # If the form has been submitted...
        #
        # That means we're makinnng an issue update. So exciting. 

        events = i.apply_post(request.POST)

        iu = IssueUpdate(issue=i, 
                         internal = 'internal' in request.POST,
                         comment=request.POST['comment'],
                         user=request.user,
                         description_data={})

        errors = i.validate()
        
        for name, value_list in iu.validate().iteritems():
            if name in errors:
                errors[name].extend(value_list)
            else:
                errors[name]=value_list

        if not errors:

            iu.save()

            events.extend(handle_files(i, iu, request.FILES))
            events.extend(send_email('web_update', request.POST, i, iu))
                               
            iu.description_data={'type':'web','events':events,'by':request.user.username}

            Event.fire(['web_update','update'], i, iu)

            i.save()
            iu.save()


            if 'update_dependants' in request.POST:
                update_dependants(i, iu, request.POST, set())

            return HttpResponseRedirect('/tuit/ticket/view/%d' % i.id) # Redirect after successfull POST
        # We failed. Show errors!
        logging.getLogger('ticket').error('Tried to create issue update, but got the following errors: %s' % str(errors));
        keys['errors'] = errors
        keys['update']=iu

        keys['messages'] += format_errors(errors)

    keys['internal_default_mail_json'] = to_json(properties['web_internal_default_mail'])
    keys['external_default_mail_json'] = to_json(properties['web_external_default_mail'])

    keys['title'] = _('Viewing %(issue_type)s "%(id)d - %(subject)s"')% {'id': i.id, 'issue_type':i.type.name, 'subject':i.subject}
    keys['issue'] = i
    keys['kb_name'] = studly(i.subject)

    insert_view_data(keys, request, properties['web_external_default_mail'])
    return tuit_render('ticket_view.html', keys, request)
    

def send_email(template_name, post, issue, update=None, **kw):
    """
    Send an email defined by template emplate_name to user groups
    defined by post about the specified issue.
    """
    events=[]
    e=EmailTemplate.objects.filter(name=template_name)
#    print('We have %d templates of specified type' % len(e)) 
    if len(e) > 0:
        e=e[0]
        recipients = filter(lambda x: (x + '_email') in post, ['assigned_to','requester','co_responsible','cc'])
        events.extend(e.send(recipients, issue=issue, update=update, **kw))
    else:
        logging.getLogger('ticket').error('No email template of type %s could be found' % template_name)
    return events

@login_required
def attachment(request, id):
    """
    Download an update attachment.
    """
    att = IssueAttachment.objects.get(id=id)
    res = HttpResponse(mimetype=att.mime)
    res.write(att.data)
    return res


# Login not required on purpose - we might in the future wish to use
# Norwegian in javascript for the login page.  There is nothing secret
# on this page.
#
# Fixme: Move to new location
from django.views.decorators.cache import cache_control
@cache_control(max_age=3600*24*7)
def i18n(request):
    """
    Send gettext-translated data in javascript format for various UI components.
    """

    regular = [gettext_noop('Comments'),gettext_noop('Send'),gettext_noop('No comments posted yet')]

    trans={'$.dpText.TEXT_CHOOSE_DATE': _('Choose date'),
           '$.dpText.TEXT_PREV_MONTH': _('Previous month'),
           '$.dpText.TEXT_PREV_YEAR': _('Previous year'),
           '$.dpText.TEXT_NEXT_MONTH': _('Next month'),
           '$.dpText.TEXT_NEXT_YEAR': _('Next year'),
           '$.dpText.TEXT_CLOSE': _('Close'),
           'Date.dayNames': [_('Sunday'),_('Monday'),_('Tuesday'),_('Wednesday'),_('Thursday'),_('Friday'),_('Saturday'),],
           'Date.monthNames': [_('January'), _('February'), _('March'), _('April'), _('May'), _('June'), _('July'), _('August'), _('September'), _('October'), _('November'), _('December')],
           }

    for i in regular:
        trans["tuit.translations[" + to_json(i)+"]"] = _(i)
#    Cache-Control: private, max-age=3600, must-revalidate
    return tuit_render('i18n.js', {'strings':trans}, request)

@login_required
def email(request, id):
    """
    Send an email
    """
    i = Issue.objects.get(id=id)
    att = filter(lambda a: ('attachment_%d'%a.id) in request.POST, 
                 IssueAttachment.objects.filter(issue=i))

    upd = filter(lambda u: ('update_%d'%u.id) in request.POST, 
                 i.updates)


    template_name ='web_resend'
    e=EmailTemplate.objects.filter(name=template_name)
#    print('We have %d templates of specified type' % len(e)) 

    name = request.POST['email']
    user = get_user(name)
    if user is None:
        user = make_contact(name)

    ok = True
    error = ''

    if user is None:
        ok = False
        error = _("Invalid email address: %s") % name 

    if len(e) > 0:
        e=e[0]
        print request.POST
        e.send(user, issue=i, update=None, attachments=att, filtered_updates = upd)
    else:
        ok = False
        logging.getLogger('ticket').error('No email template of type %s could be found' % template_name)
        error = _("No email template named %s could be found") % template_name
    return tuit_render('ticket_email.html', {'ok':ok,'email':name,'issue':i, 'error':error}, request)


@login_required
def user_list(request):
    if not request.user.is_staff:
        return None


    items = User.objects.all()
    print items

    username = request.GET.get('username', '')
    if username:
        items = items.filter(username__contains = username)
    first_name = request.GET.get('first_name', '')
    if first_name:
        items = items.filter(first_name__contains = first_name)
    last_name = request.GET.get('last_name', '')
    if last_name:
        items = items.filter(last_name__contains = username)

    items = items.order_by('username')

    keys={'title': _("Manage user profiles"),
          'user_list_widget': tuit.home.widget.Widget(
            _('Matching user profiles'),
            items,
            request,
            'user_list',
            item_count=10,
            class_names="widget_2"),
          'username': username,
          'first_name': first_name,
          'last_name': last_name
          }
    
    return tuit_render('user_list.html', keys, request)


@login_required
def user_edit(request,id=None):
    if not request.user.is_staff:
        return None

    errors = {}

    if id == 'new':
        user_profile = UserProfile()
        user_profile.user = django.contrib.auth.models.User()
        pass
    else:
        try:
            user_profile = UserProfile.objects.get(user = int(id))
        except:
            user = django.contrib.auth.models.User.objects.get(id=int(id))
            user_profile = UserProfile()
            user_profile.user = user

    if request.method == 'POST': 

        # if request.POST['user_password'] != request.POST['user_password_retype']:
        #     errors['password'] = ["Passwords don't match"]
        # elif id == 'new' and not request.POST['user_password']:
        #     errors['password'] = ["Passwords is empty"]
        # elif not request.POST['user_username']:
        #     errors['username'] = ["Username is empty"]
        # else:
        # del request.POST['user_password_retype']
        # if not request.POST['user_password']:
        #     del request.POST['user_password']
        for name, value in request.POST.iteritems():
            if name.startswith('user_'):
                setattr(user_profile.user, name[len('user_'):], value[0])
            else:
                setattr(user_profile, name, value[0])
        user_profile.save()
        user_profile.user.save()
        return HttpResponseRedirect("..")
    data = {
        "edit_user": user_profile,
        'errors': errors,
        'messages': format_errors(errors)
        }
    return tuit_render('user_edit.html', data, request)

@login_required
def user_remove(request,id=None):
    user = django.contrib.auth.models.User.objects.get(id=int(id))
    user.delete()
    return HttpResponseRedirect("../..")

