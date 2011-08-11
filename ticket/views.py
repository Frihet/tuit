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
#from django.db.models import Q

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
    keys['dependency_types'] = IssueDependencyType.objects.all().order_by('name')
    for box in ('update_dependants','internal','assigned_to_email','requester_email','co_responsible_email','cc_email'):
        if request.method=='POST':
            if box in request.POST:
                keys[box]='checked'
        elif box in default_checked:
            keys[box]='checked'

def get_server_files(post):
    if 'upload_count' not in post:
        return []
    def format_server_file(idx):
        save_dir = properties['attachment_directory']
        full_dir=save_dir + "/temp/"
        f = open( full_dir + post['upload_localname_'+str(idx)],'r')
        content = f.read()
        f.close()
        return {'localname':post['upload_localname_'+str(idx)],
                'content': content,
                'filename': post['upload_filename_' + str(idx)],
                'mime': post['upload_mime_' + str(idx)],
                'content-type': post['upload_mime_' + str(idx)],
                'idx':idx}
    return map(format_server_file, range(int(post['upload_count'])))

def handle_files( issue, update, files, post ):
    res=[]
#    print files
    idx = 0
    for file in get_server_files(post):
        IssueAttachment.create(issue, update, file['content'], file['filename'], file['content-type'], idx)
        idx += 1
    for filename in files:
        file = files[filename]
#        print file
#        IssueAttachment.create(issue, update, file.read(), file.name, file.content_type)
        IssueAttachment.create(issue, update, file['content'], file['filename'], file['content-type'], idx)
        idx += 1
    return res

def handle_files_error( issue, update, files, post ):
    """
    When a validation error occured, we still need to save our
    precious files, so that the user doesn't have to reupload them.
    """
    res=get_server_files(post)
#    print files
    idx = len(res)
    for filename in files:
        file = files[filename]

        save_dir = properties['attachment_directory']
        full_dir=save_dir + "/temp"
        import os, tempfile
        try:
            os.makedirs(full_dir)
        except:
            pass
        fullname = tempfile.mkstemp(dir=full_dir)
        os.close(fullname[0])
        f = open(fullname[1], 'w')
        try:
            f.write(file['content'])
        finally:
            f.close()
        res.append({"localname": fullname[1].split('/')[-1],
                    'filename':file['filename'],
                    'content-type':file['content-type'],
                    'mime':file['content-type'],
                    'idx':idx})
        idx += 1
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

def parse_post_dependencies(post):
#    return [{'description': "Trololololo: Ha ha ha!",'idx':0,'id':3180,'type':'1_reverse'}]
    res = [];
    
    prog = re.compile(r"dependency_([0-9]*)_id")
    for i in post:
        result = prog.match(i)
        if result:
            idx = result.group(1)
            id = post[i]
            type = post["dependency_"+idx+"_type"]
            type_arr = type.split('_');
            t = IssueDependencyType.objects.get(id=int(type_arr[0]))
            type_desc = ""
            if len(type_arr) == 1:
                type_desc = t.name
            else:
                type_desc = t.reverse_name
            i = Issue.objects.get(id=int(id))
            description = "%s: %s - %s" % (type_desc, i.id, i.subject)
            res.append({'description': description,'idx':idx,'id':id,'type':type})
            
    return res

def parse_issue_dependencies(issue):
    res = [];
    idx = 0
    for dep in issue.dependencies.all():
        description = "%s: %s - %s" % (dep.type.name, dep.dependency.id, dep.dependency.subject)   
        res.append({
                'description': description,
                'idx':idx,
                'id':dep.dependency.id,
                'type':dep.type.id})
        idx+=1;

    for dep in issue.dependants.all():
        description = "%s: %s - %s" % (dep.type.reverse_name, dep.dependant.id, dep.dependant.subject)   
        res.append({
                'description': description,
                'idx':idx,
                'id':dep.dependant.id,
                'type': "%s_reverse" % dep.type.id })
        idx+=1;

    return res

@login_required
def move(request):
    key_out={}
    print 'aaa'

    try:
        id = request.POST['id']
        t_id = request.POST['type']
        i=Issue.objects.get(id=id)
        t=IssueType.objects.get(id=t_id)
        i.type = t
        errors = i.validate()
        print 'bbb'
        if not errors:
            # This try catch block is added by Nikola as a solution for
            # problem of changing type of issue causes type error
            try:
                i.save()
            except:
                pass
            url = '/tuit/ticket/view/%d' % i.id 
            return HttpResponseRedirect(url)
        key_out['errors'] = errors
    except:
        traceback.print_exc()
        pass
    print 'ccc'
    return tuit_render('ticket_view.html', key_out, request)
    
    



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
    keys['file_count'] = 0
    i = Issue()
    keys['dependencies'] = []
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
        
            if not errors:
                events.extend(handle_files(i, None, request.FILES, request.POST))
                events.extend(send_email('web_create', request.POST, i, None))

                i.description_data={'type':'web','events':events, 'by':request.user.username}
                
                # Fire of event handler
                Event.fire(['web_create','create'], i)
                errors = i.validate()
                if not errors:
                    i.save()
                
                    # If everything went ok with form submission, this is where we return
                    logging.getLogger('ticket').info('Created issue with id %d' % i.id)

                    url = '/tuit/ticket/view/%d' % i.id 
                    if 'continue' in request.POST:
                        url = '/tuit/ticket/new/?type=' + cgi.escape(i.type.name)
                    elif 'new_url' in request.POST:
                        url = request.POST['new_url']
                    return HttpResponseRedirect(url)

        # This code is only reached oif we get an error while processing the form
        logging.getLogger('ticket').error('Tried to create issue, but got the following errors: %s' % str(errors));
        keys['errors'] = errors
        keys['messages'] += format_errors(errors)
        keys['files'] = handle_files_error(i, None, request.FILES, request.POST)
        keys['file_count'] = len(keys['files'])

        keys['dependencies'] = parse_post_dependencies(request.POST)
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

    for i_d in issue.dependants.all():
        i = i_d.dependant
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

    if not request.user.is_staff and i.requester != request.user:
        return tuit_render('ticket_view.html', {}, request)

    keys = request.POST.copy()
    keys['messages'] = ""
    keys['update']=None
    keys['show_internal'] = request.user.has_perm('ticket.view_internal')
    keys['file_count'] = 0
    keys['dependencies'] = parse_issue_dependencies(i)

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

            Event.fire(['web_update','update'], i, iu)
            errors = i.validate()
            if not errors:
            
                iu.save()
                events.extend(handle_files(i, iu, request.FILES, request.POST))
                events.extend(send_email('web_update', request.POST, i, iu))
                               
                iu.description_data={'type':'web','events':events,'by':request.user.username}

                i.save()
                iu.save()

                if 'update_dependants' in request.POST:
                    update_dependants(i, iu, request.POST, set())

                return HttpResponseRedirect('/tuit/ticket/view/%d' % i.id) # Redirect after successfull POST
        # We failed. Show errors!
        logging.getLogger('ticket').error('Tried to create issue update, but got the following errors: %s' % str(errors));
        keys['errors'] = errors
        keys['update']=iu

        keys['dependencies'] = parse_post_dependencies(request.POST)
        keys['files'] = handle_files_error(i, None, request.FILES, request.POST)
        keys['file_count'] = len(keys['files'])

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

    items = User.objects
    print items

    search = request.GET.get('search', '')
    if search:
        items = items.filter(username__contains = search) | items.filter(first_name__contains = search) | items.filter(last_name__contains = search) | items.filter(email__contains = search)
    else:
        items = items.all()

    items = items.order_by('username')

    keys={'title': _("Manage user profiles"),
          'user_list_widget': tuit.home.widget.Widget(
            _('Matching user profiles'),
            items,
            request,
            'user_list',
            item_count=10,
            class_names="widget_2"),
          'search': search,
          }
    
    return tuit_render('user_list.html', keys, request)


@login_required
def user_edit(request,id=None):
    if not request.user.is_staff and request.user.id != int(id):
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

