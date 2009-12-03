# Models for the ticket app of tuit
# -*- coding: utf-8 -*-

from django.db import models
from django.contrib.auth.models import *
from django.utils.html import strip_tags
from tuit.html2text import html2text
from tuit.util import ModelDict, properties
from django.utils.translation import gettext as _
from tuit.json import to_json, from_json
from tuit.util import email_valid, escape_recursive, encode_recursive
from tuit.ticket.templatetags.tuit_extras import datetime_format, date_format

import smtplib
import email.mime.text
import email.mime.multipart
import re
import cgi


# Fixme:
#
# Move the util functions to their own namespace/file, perhaps called
# util?  Or would that name be confusing, we already have a util
# app... These are issue specific utils. Either way, they're polluting
# the model namespace where they are... :-/


def remove_html_tags(data):
    import re
    p = re.compile(r'<.*?>')
    return p.sub('', data)

def format_user(u):
    """
    Display user information
    """
    if u:
        return "%s - %s %s" % (u.username, u.first_name, u.last_name)
    return ""

def format_user_email(u):
    """
    Display user information
    """
    return "%s %s <%s>" % (u.first_name, u.last_name, u.email)
    

def user_name(u):
    """
    Display user information
    """
    return "%s %s" % (u.first_name, u.last_name)

User.format = property(format_user_email)
User.name = property(user_name)

def get_user(name):
    """
    Return user with specified name, or None if no such user exists.
    """
    try:
        uname = name.split(' ')[0]
        return User.objects.get(username=uname)
    except User.DoesNotExist:
        return None

def get_issue(name):
    """
    Return issue with specified id, or None if no such issue exists.
    """
    try:
        id = int(name.split(' ')[0])
        return Issue.objects.get(id=id)
    except:
        return None


def make_contact(text):
    """Returns the contact object with the specified email if it
    exists, or creates one if the email address is valid. In cas of an
    invalid email, return None."""
    email=text
    name=""
    
    try:
        m=re.search(r'(.*[^ ]) *<([^\s<>]+@[a-z0-9_.]+)>', text)
        name= m.groups()[0]
        email= m.groups()[1]
    except:
        import traceback
        traceback.print_exc()
        pass
#    print 'name',name
#    print 'email',email

    try:
        c = Contact.objects.get(email__iexact=email) 
        if name and name != c.name:
            c.name = name
            c.save()
        return c
    except Contact.DoesNotExist:
        if email_valid(email):
            c=Contact(email=email, name=name)
            c.save()
            return c
    return None

# Here begins the list of models proper

class Status(models.Model):
    """
    Status of a ticket, e.g. 'Closed', 'Open', etc.
    """

    name = models.CharField(maxlength=64, unique=True)

    def __str__(self):
        return self.name

    class Admin: 
        pass

    class Meta:
        ordering = ['name']
        verbose_name_plural = _('statuses')
        verbose_name = _('status')


class IssueType(models.Model):
    """
    Type of issue, e.g. incident, problem or RfC.
    """
    name = models.CharField(maxlength=64, unique=True)
    has_location = models.BooleanField()
    extra_fields = models.ManyToManyField("IssueField", blank=True)

    def __str__(self):
        return self.name

    class Admin: 
        pass

    class Meta:
        ordering = ['name']
        verbose_name_plural = _('types of issues')
        verbose_name = _('type of issue')

class Category(models.Model):
    """
    A ticket category is a simple one-level dropdown (select)
    box. This table contains all the existing dropdown items, e.g. 'MS
    Office' or 'Citrix'.

    This is significantly simpler than the 3 (or was it 4?) level
    category system used previously. The remaining levels are replaced
    by the CMDB. 
    """
    name = models.CharField(maxlength=64, unique=True)

    def __str__(self):
        return self.name

    class Admin: 
        pass

    class Meta:
        ordering = ['name']
        verbose_name_plural = _('issue categories')
        verbose_name = _('issue category')


class QuickFill(models.Model):
    name = models.CharField(maxlength=512, unique=True)

    def __str__(self):
        return self.name

    def __to_json__(self):
        return {
            '__jsonclass__':['QuickFill', self.id],
            'name':self.name,
            'id':self.id,
            'item':list(self.quickfillitem_set.all())}

    class Admin: 
        pass

    class Meta:
        ordering = ['name']
        verbose_name_plural = _('quick fills')
        verbose_name = _('quick fill')


class QuickFillField(models.Model):
    name = models.CharField(maxlength=512)
    description = models.CharField(maxlength=512)

    def __str__(self):
        return self.description
    
    class Admin: 
        pass

    class Meta:
        ordering = ['name']
        verbose_name_plural = _('Field for quick fills')
        verbose_name = _('Field for quick fill')
        
    
class QuickFillItem(models.Model):
    fill = models.ForeignKey(QuickFill)
    field = models.ForeignKey(QuickFillField)
    value = models.CharField(maxlength=32000)
    
    def __str__(self):
        return str(self.fill) + ": " + str(self.field)
    
    def __to_json__(self):
        return {
            '__jsonclass__':['QuickFillItem', self.id],
            'field':self.field.name,
            'value':self.value}

    class Admin: 
        pass

class Contact(models.Model):
    """
    A contact is a person who is not a user, but still is included in
    a ticket cc list or the originator of an issue update.
    """
    email = models.CharField(maxlength=320, unique=True)
    name = models.CharField(maxlength=512,blank=True)
    
    @property
    def description(self):
        return self.name or "(Unknown)"

    @property
    def format(self):
        if self.name:
            return "%s <%s>" % (self.name, self.email)
        return self.email

    @property
    def tuit_description(self):
        return cgi.escape(self.format)

    @property
    def first_name(self):
        return ""

    @property
    def last_name(self):
        return self.name

    def __str__(self):
        return self.format

    class Admin:
        pass

    class Meta:
        ordering = ['name']
        verbose_name_plural = _('external contacts')
        verbose_name = _('external contact')
        

class CiDependency(models.Model):
    """
    A ticket dependency on a CI from the CMDB. Because we want to
    allow the CMDB and the issue system to run on different servers
    without dependencies, the ci_id here is in fact _not_ a true
    foreign key, it is simply an integer.
    """
    issue = models.ForeignKey("Issue")
    ci_id = models.IntegerField()
    description = models.CharField(maxlength=512)
    view_order = models.IntegerField()

    class Meta:
        unique_together = (('issue','ci_id'),)

class Issue(models.Model):
    """
    This is the main issue table. Contains the bulk of the data about
    an issue except for updates.

    Note that this data is not static - the status column in this
    table always has the latest status of the issue, not any
    history. We need to check the json-data to find the historic data
    for a specific point in time.

    This class has a very large number of properties. These are used
    during form submission to provide mapping from string data as
    provided by a web form into issue data. For a db field
    (e.g. requester) there will typically be a property
    requester_string, which will perform mapping junction table
    traversal and everything else that may be needed in order to parse
    and perform the assignment.

    These properties are in turn typically used by the apply_post
    function. Any errors encounders are stored in the __errors member.
    """

    current_status = models.ForeignKey(Status)
    type = models.ForeignKey(IssueType)
    category = models.ForeignKey(Category)
    assigned_to = models.ForeignKey(User, null=True, blank=True, related_name='assigned')
    co_responsible = models.ManyToManyField(User, related_name='co_responsible_for')
    cc_user = models.ManyToManyField(User, related_name='cc_on')
    cc_contact = models.ManyToManyField(Contact, related_name='cc_on')
    requester = models.ForeignKey(User, related_name='requested')
    subject = models.CharField(maxlength=256)
    
    # HTML is ok in this field
    description = models.CharField(maxlength=8192)
    impact = models.IntegerField()
    urgency = models.IntegerField()
    creation_date = models.DateTimeField(auto_now_add=True)
    dependencies = models.ManyToManyField('self', symmetrical=False, related_name='dependants')
    
    # This field contains optional additional information about this
    # update, serialized in the JSON format. Leave it blank.
    create_description = models.CharField(maxlength=8192)
    creator = models.ForeignKey(User, related_name='created')

    location = models.CharField(maxlength=256, blank=True)
    building = models.CharField(maxlength=256, blank=True)
    office = models.CharField(maxlength=256, blank=True)

    # Any errors encoundered during apply_post go here.
    __errors={}

    # Cached list of extra fields.
    __extra_fields = None

    # Cached list of dependencies.
    __ci_dependencies = None

    # Dummy variable needed to get some searches working - never use it for anything!!!
    priority_placeholder=None

    @property
    def html_default_columns(self):
        """
        The default columns to show when displaying an issue in a Widget
        """
        return ((_('Issue name'),'name'),(_('Priority'),'priority'),(_('Requester'),'requester'))

    @property
    def extra_fields(self):
        """
        Return extra fields of this issue type
        """
        if self.__extra_fields is None:
            try:
                self.load_extra_fields()
            except:
                import traceback as tb
                tb.print_exc()
                raise
        return self.__extra_fields

    def load_extra_fields(self):
        values = dict(map(lambda x:(x.field.name,x),self.issuefieldvalue_set.all()))
        dropdown_values = dict(map(lambda x:(x.field.name,x),self.issuefielddropdownvalue_set.all()))
        value_items = dict(map(lambda x:(x.field.name,x),self.issuefielddropdownvalue_set.all()))
        def process_field(f):
            class FieldData(object):
                def __init__(self, field, value):
                    self.field = field
                    self.value=value
                    
                def render_input(self):
                    return self.field.render_input(self.value)

                def render_value(self):
                    return self.field.render_value(self.value)

                def __str__(self):
                    return "'%s' '%s'" % (self.field, self.value)

                def __repr__(self):
                    return self.__str__()
            if f.field_type == 'dropdown':
                value = IssueFieldDropdownValue(issue=self,
                                                field=f)
                if f.name in dropdown_values:
                    value = dropdown_values[f.name]
            else:
                value = IssueFieldValue(issue=self,
                                        field=f,
                                        value='')
                if f.name in values:
                    value = values[f.name]


            return FieldData(f, value)
        self.__extra_fields = map(process_field, self.type.extra_fields.all().order_by('view_order'))
#        print self.__extra_fields


    def save(self):
        """
        Save not only this issue, but also all of its extra fields.
        """
        models.Model.save(self)
        for i in self.extra_fields:
            i.value.issue=self
            i.value.save()

    @property
    def has_location(self):
        return self.type.has_location

    @property
    def html(self):
        """
        Returns an html-stykle anchor link to the issue
        """
        return "<a href='%s'>%d - %s</a>" % (self.url_internal,self.id, self.subject)

    def html_row(self, columns):
        """
        Used for widget rendering
        """
        res = ""

        for col in columns:
            res += self.html_cell(col)
            
        return "<tr>%s</tr>" % res

    def html_cell(self, col):
        """
        Used for widget rendering
        """
        try:
            def user_desc(user):
                if not user:
                    return ''
                return user.tuit_description

            return "<td>" + {
                'name':lambda: "<a href='%s'>%d - %s</a>" % (self.url_internal,self.id, self.subject),
                'priority':lambda: "%s" % self.priority,
                'owner':lambda: user_desc(self.assigned_to),
                'requester':lambda: user_desc(self.requester),
                }[col]() + "</td>"
        except:
            logging.getLogger('ticket').error('Issue.html_cell failed while fetching column', col,'for issue',self.id)
            raise
        

    @property
    def priority(self):
        return self.impact+self.urgency

    def set_description_data(self, data):
        self.create_description = to_json(data).encode('utf-8')

    def get_description_data(self):
        return encode_recursive(from_json(self.create_description))

    description_data = property(get_description_data, set_description_data)
    
    def apply_post(self, values):
        """
        This is the main work engine of incident and update
        creation. It takes a bunch of incident data in string format
        (as supplied by a web form) and maps it to the correct fields,
        performing foreign key lookups, traversing junction tables,
        etc. as needed.
        """

        events = []
        #print 'Applying values', values
        #print 'Applying post to issue %d'%self.id
        #print 'requester is', self.requester
        old = {}

        attrs = ['assigned_to_string','impact_string','urgency_string','requester_string','current_status_string','subject','description','category_string','location','building','office']

        if self.id:
            attrs.extend(['ci_string','co_responsible_string','cc_string','requester_string','dependencies_string'])

        for el in attrs:
            old[el] = getattr(self,el)

        for el in attrs:
            if el in values:
                new = values[el]
                if old[el] != new:
                    events.append({'field':el, 'old':old[el], 'new':new})
                    setattr(self, el, values[el])
        
        for el in self.extra_fields:
            if el.field.name in values:
                if el.field.field_type == 'dropdown':
                    old = None
                    try:
                        old = el.value.item.id
                    except:
                        pass
                    try:
                        new = int(values[el.field.name])
                    except:
                        self.error(el.field.name, _('Invalid value: %s.') % values[el.field.name])
                        continue
                    if old != new:
                        el.value.item = IssueFieldDropdownItem.objects.get(id=new)
                        events.append({'field':el.field.name, 'old':old, 'new':new})

                else:
                    old = el.value.value
                    new = values[el.field.name]
                    if old != new:
                        el.value.value = new
                        events.append({'field':el.field.name, 'old':old, 'new':new})
                    if new == "" and not el.field.blank:
                        self.error(el.field.name, _('This field is required.'))
            elif not el.field.blank:
                self.error(el.field.name, _('This field is required.'))

        return events

    def error(self, name, msg):
        """
        Add new error to form application/validation pass
        """
        if name not in self.__errors:
            self.__errors[name]=[]
        self.__errors[name].append(msg)

    def set_current_status_string(self, value):
        try:
            self.current_status = Status.objects.get(id=int(value))
        except:
            self.error('current_status', _("Invalid status"))

    def get_current_status_string(self):
        if self.id and self.current_status:
            return str(self.current_status.id)
        else:
            return ''

    current_status_string = property(get_current_status_string, set_current_status_string)

    def set_category_string(self, value):
        try:
            self.category = Category.objects.get(id=int(value))
        except:
            self.error('category', _("Invalid category %d") % value)

    def get_category_string(self):
        if self.id and self.category:
            return str(self.category.id)
        else:
            return ''

    category_string = property(get_category_string, set_category_string)

    def get_assigned_to_string(self):
        if self.id and self.assigned_to:
            return format_user(self.assigned_to)
        else:
            return ''

    def set_assigned_to_string(self, value):
        if value == "" or value is None:
            self.assigned_to=None
            return
        u = get_user(value)
        if u is None:
            self.error('assigned_to', _("Unknown user: %(value)s, %(type)s") % {'value':value, 'type':str(type(value))})
        self.assigned_to = u

    assigned_to_string = property(get_assigned_to_string, set_assigned_to_string)
        
    def get_requester_string(self):
        if self.id and self.requester:
            return format_user(self.requester)
        else:
            return ''
        
    def set_requester_string(self, value):
        if value == "" or value is None:
            self.requester=None
            return
        u = get_user(value)
        if u is None:
#            print 'DUN DUN DUN'
            self.error('requester', _("Unknown user: %s") % value)
        self.requester = u

    requester_string = property(get_requester_string, set_requester_string)
        
    def get_cc_string(self):
        if self.id is None:
            return ""
        return "\n".join(map(lambda x: x.format,self.cc_contact.all())+map(lambda x: "%s - %s %s" % (x.username, x.first_name, x.last_name),self.cc_user.all()))

    def set_cc_string(self, val):
        self.cc_contact.clear()
        self.cc_user.clear()
        for name in val.split('\n'):
            name=name.strip()
            if name == '':
                continue
            u = get_user(name)
            if u is None:
                c = make_contact(name)
                if c:
                    self.cc_contact.add(c)
                else:
                    self.error('cc',_('Invalid user or contact: %s') % name)
            else:
                self.cc_user.add(u)

    cc_string = property(get_cc_string, set_cc_string)

    def get_co_responsible_string(self):
        if self.id is None:
            return ""
        return "\n".join(map(lambda x: "%d - %s %s" % (x.username, x.first_name, x.last_name), self.co_responsible.all()))


    def set_co_responsible_string(self, val):
        self.co_responsible.clear()
        for name in val.split('\n'):
            name=name.strip()
            if name == '':
                continue
            u = get_user(name)
            if u is None:
                self.error('co_responsible', _('Invalid user: %s') % name)
            else:
                self.co_responsible.add(u)


    co_responsible_string = property(get_co_responsible_string, set_co_responsible_string)

    def validate(self):
        """
        Perform regular validation but also return any errrors from apply_post()-call.
        """
        res = self.__errors.copy()
        for name, value_list in models.Model.validate(self).iteritems():
            if name in res:
                res[name].extend(value_list)
            else:
                res[name]=value_list
        return res

    def get_impact_string(self):
        return str(self.impact)

    def set_impact_string(self, value):
        try:
            v=int(value)
            if v < 1 or v > 5:
                self.error('impact', _('Value out of range: %d') % v)
            else:
                self.impact=v
        except TypeError:
            self.error('impact', _('Not an integer number: %s') % value)

    impact_string = property(get_impact_string, set_impact_string)

    def get_urgency_string(self):
        return str(self.urgency)

    def set_urgency_string(self, value):
        try:
            v=int(value)
            if v < 1 or v > 5:
                self.error('urgency', _('Value out of range: %d') % v)
            else:
                self.urgency=v
        except TypeError:
            self.error('urgency', _('Not an integer number: %s') % value)

    urgency_string = property(get_urgency_string, set_urgency_string)

    def get_dependencies_string(self):
        if self.id is None:
            return ""
        return "\n".join(map(lambda x: "%d - %s" % (x.id, x.subject),self.dependencies.all()))
    
    def set_dependencies_string(self, val):
        self.dependencies.clear()
        for name in val.split('\n'):
            name=name.strip()
            if name == '':
                continue
            i = get_issue(name)
            if i is None:
                self.error('dependencies_string',_('Invalid issue: %s') % name)
            else:
                self.dependencies.add(i)

    dependencies_string = property(get_dependencies_string, set_dependencies_string)

    def get_ci_string(self):
        try:
            if self.id is None:
                return ""
            return "\n".join(map(lambda x: "%d - %s" % (x.ci_id, x.description),
                                 list(self.cidependency_set.order_by('view_order'))))
        except:
            import traceback as tb
            tb.print_exc()
            raise

    def set_ci_string(self, value):

        def get_ci_id(name):
            try:
                return int(name.split(' ')[0])
            except:
                return None

        self.cidependency_set.all().delete()
        i=0
        for name in value.split('\n'):
            name=name.strip()
            if name == '':
                continue
            id = get_ci_id(name)
            desc = name.split(' ')[2]
            self.cidependency_set.create(ci_id=id, description = desc, view_order = i)
            i = i+1

    ci_string = property(get_ci_string, set_ci_string)

    @property 
    def url(self):
        return properties['site_url'] + self.url_internal

    @property 
    def url_internal(self):
        return properties['site_location'] + ('/ticket/view/%d' % self.id)

    @property
    def dependencies_list(self):
        if self.id is None:
            return []
        return self.dependencies

    @property
    def co_responsible_list(self):
        if self.id is None:
            return []
        return self.co_responsible.all()

    @property
    def ci_list(self): 
        def frmt(line):
            
            arr = line.split(' ', 2)
            return {'id':arr[0], 'name':arr[2], 'url':'/FreeCMDB/ci/%s' %arr[0]}

        return map(frmt,filter(lambda x:x.strip() != "",self.ci_string.split("\n")))

    @property
    def updates(self):
        if self.id is None:
            return []
        return self.issueupdate_set.all().order_by('creation_date')

    @property
    def last_update(self):
        if self.id is None:
            return None

        all = self.updates
        str(all)
        if len(all) > 0:
            return all[len(all)-1]
        return None

    @property
    def last_update_date(self):
        if self.id is None:
            return self.creation_date
        u = self.last_update
        if u:
            return u.creation_date
        return self.creation_date

    def __getattr__(self, name):
        """
        Conveniance function. You may use extra fields as regular
        attributes if you wish.
        """
        if name[0] == '_':
            raise AttributeError()
                
        extra_fields = set(map(lambda x:x.name, self.type.extra_fields.all()))

        for val in list(self.issuefieldvalue_set.all()):
            if val.field.name == name:
                return val.value
        print "Could not find attribute '%s'" % name
        raise AttributeError()

    def __hash__(self):
        return hash(self.id)

    def __cmp__(self, other):
        return cmp(self.id, other.id)

    class Meta:
        permissions = (
            ('view_internal', _('Can view internal updates')),
            ('is_sd', _('Is Service Desk staff')),
            )
    

class IssueField(models.Model):
    """
    This is an extra issue field, used to create extra fields for
    specific issue types. E.g. the RfC issue type should have various
    extra dropdowns and text fields that other issue types do not
    have.
    """

    FIELD_TYPE_CHOICES = (
        ('text',_('Text field')),
        ('grading',_('Grade from 1 to 5')),
        ('dropdown',_('Dropdown box')),
        ('textarea',_('Multiline text area')),
        ('date',_('Date')),
        )

    # This is a short 'slug' name, should only countain letters,
    # numbers and underscores. Will not be shown to the user.
    name = models.CharField(maxlength=64)
    
    # The human-eradable name 
    short_description = models.CharField(maxlength=64)
    long_description = models.CharField(maxlength=256)
    field_type = models.CharField(maxlength=16, choices=FIELD_TYPE_CHOICES)
    blank = models.BooleanField()
    view_order = models.IntegerField()

    def __str__(self):
        return self.short_description

    def render_input(self, data):
        """
        FIXME: This function needs a bit of cleanup.

        Render an extra field in the correct manner depending on field type.
        """
        try:
            if self.field_type == 'text':
                return "<input value='%s' id='%s' name='%s' />" % escape_recursive(data.value, self.name, self.name)
            elif self.field_type == 'textarea':
                return "<textarea class='rich_edit' id='%s' style='height:20em; width:80%%;' name='%s' />%s</textarea>" % escape_recursive(self.name, self.name, data.value)
            elif self.field_type == 'date':
                return "<input name='%s' id='%s' class='date_picker' value='%s'>" % escape_recursive(self.name, self.name, data.value)
            elif self.field_type == 'dropdown':
                sel = "<select name='%s' id='%s'>" % escape_recursive(self.name, self.name)
                id = None
                try:
                    id = data.item.id
                except:
                    pass

                def format_option(item):
                    sel = ""
                    if id == item.id:
                        sel = 'selected'
                    return "<option value='%d' %s>%s</option>"%(item.id, sel, escape_recursive(item.name))  
                opt = "\n".join(map(format_option, self.issuefielddropdownitem_set.order_by('name')))
                return sel + opt + "</select>"
            elif self.field_type == 'grading':
                def format_grade(num):
                    checked = ""
                    if data.value == str(num):
                        checked = "checked='yes'"
                    return "<input class='radio' type='radio' id='%(name)s_%(num)d' name='%(name)s' value='%(num)d' %(checked)s /><label for='%(name)s_%(num)d'>%(num)d</label>" % {'name':self.name, 'num': num, 'checked':checked}

                return "\n".join(map(format_grade, range(1,6)))


        except:
            import traceback
            traceback.print_exc()
            raise

        return None

    def render_value(self, data):
        if self.field_type == 'dropdown':
            return escape_recursive(data.item.name)
        if self.field_type == 'textarea':
            return data.value

        return escape_recursive(data.value)

    class Admin: 
        pass

    class Meta:
        ordering = ['short_description']
        verbose_name_plural = _('Extra fields for issues')
        verbose_name = _('Extra field for issues')
       

class IssueFieldDropdownItem(models.Model):
    """
    A row in this table represents a dropdown item in for a dropdown
    (select) widget.
    """
    field = models.ForeignKey(IssueField)                     
    name = models.CharField(maxlength=64)

    def __str__(self):
        return "%s (%s)" % (self.name, self.field.short_description)

    class Admin: 
        pass

    class Meta:
        ordering = ['name']
        verbose_name_plural = _('items for extra fields of dropdown type')
        verbose_name = _('item for extra field of dropdown type')
        
    
class IssueFieldDropdownValue(models.Model):      
    """
    A row in this table represents a selected value for a dropdown widget. 
    """
    issue = models.ForeignKey(Issue)                          
    field = models.ForeignKey(IssueField)                     
    item = models.ForeignKey(IssueFieldDropdownItem)                     

class IssueFieldValue(models.Model):                          
    """
    A value for a 'ticket_issuefield' extra field in text format.
    """

    issue = models.ForeignKey(Issue)                          
    field = models.ForeignKey(IssueField)                     
    value = models.CharField(maxlength=8192)                  
   
class IssueUpdate(models.Model):
    """
    This is a single update for a given ticket. It can represent
    either an update sent through the web interface or through email.
    """


    #Either user_id or contact_id must always be set, but never
    #both. The contact or user pointed to is the originator of this
    #update.
    user = models.ForeignKey(User,null=True,blank=True)
    contact = models.ForeignKey(Contact,null=True,blank=True)
    
    # HTML ok in this field
    comment = models.CharField(maxlength=8192)

    # This field contains optional additional information about this
    # update, serialized in the JSON format.
    description = models.CharField(maxlength=8192)

    creation_date = models.DateTimeField(auto_now_add=True)

    # If set, this update should only be visible to the SD staff
    internal = models.BooleanField()
    issue = models.ForeignKey(Issue)

    @property
    def creator(self):
        if self.user:
            return self.user
        return self.contact

    def set_description_data(self, data):
        self.description = to_json(data).encode('utf-8')

    def get_description_data(self):
        return encode_recursive(from_json(self.description))

    description_data = property(get_description_data, set_description_data)

    @property
    def summary(self):
        return "%s: %s..." % (self.creator.name, remove_html_tags(self.comment)[:32])

    @property
    def html_default_columns(self):
        """
        Default columns for widget rendering.
        """
        return ((_('Issue name'),'name'),(_('Update'),'update'),(_('Priority'),'priority'),(_('Requester'),'requester'),(_('Update date'),'creation_date'))

    def html_row(self, columns):
        """
        Used for widget rendering.
        """

        res = ""

        for col in columns:
            try:
                if col == 'update':
                    def truncate(str, l):
                        if len(str) > l:
                            return str[0:l] + "..."
                        return str
                    res += "<td>"+truncate(remove_html_tags(self.comment),64)+ "</td>"

                elif col == 'creation_date':
                    res += "<td>"+datetime_format(self.creation_date)+ "</td>"
                else:
                    res += self.issue.html_cell(col)
            except:
                import traceback as tb
                tb.print_exc()
                raise
            
        return "<tr>%s</tr>" % res

    
    
class IssueUpdateAttachment(models.Model):
    """
    This table contains information about attachments. No fiels are
    stored in the DB, we only have the filename of the attachment
    proper.
    """

    # This is the issue update that included the attachment.
    update = models.ForeignKey(IssueUpdate)

    # This is the original filename for the attachment, e.g. what the file was called in the email or under what name it was uploaded.
    name = models.CharField(maxlength=8192)

    # This is the on disk filename of the attachment.
    filename = models.CharField(maxlength=8192)
    mime = models.CharField(maxlength=128)

    @property
    def url(self):
        return properties['site_url'] + properties['site_location'] + '/ticket/attachment/%d/%s' % (self.id, self.name)


class IssueFieldValue(models.Model):
    # The issue that is updated
    issue = models.ForeignKey(Issue)
    # The field that is updated
    field = models.ForeignKey(IssueField)
    # The new value
    value = models.CharField(maxlength=64)


class Property(models.Model):
    """
    Fixme: Move to separate app.

    General purpose key/value pair store. Why doesn't django have one of these OOTB?
    """

    name = models.CharField(maxlength=1024, unique=True)
    value = models.TextField(maxlength=8192)
    
    def __str__(self):
        return self.name

    class Admin: 
        pass

    class Meta:
        ordering = ['name']
        verbose_name_plural = _('properties')
        verbose_name = _('property')


class SmtpConfiguration(models.Model):
    """
    Smtp email server config data
    """
    host = models.CharField(maxlength=256)
    port = models.IntegerField()
    username = models.CharField(maxlength=256, null=True, blank=True)
    password = models.CharField(maxlength=256, null=True, blank=True)
    use_ssl = models.BooleanField()
    use_tls = models.BooleanField()

    class Admin: 
        pass

    class Meta:
        ordering = ['host']
        verbose_name_plural = _('SMTP configurations')
        verbose_name = _('SMTP configuration')
        

class ImapConfiguration(models.Model):
    """
    IMAP email server config data
    """
    host = models.CharField(maxlength=256)
    port = models.IntegerField()
    mailbox = models.CharField(maxlength=256, blank=True)
    username = models.CharField(maxlength=256, null=True, blank=True)
    password = models.CharField(maxlength=256, null=True, blank=True)
    use_ssl = models.BooleanField()
    email = models.EmailField(maxlength=320)
    name = models.CharField(maxlength=256)

    class Admin: 
        pass

    class Meta:
        ordering = ['host']
        verbose_name_plural = _('IMAP configurations')
        verbose_name = _('IMAP configuration')
        

class EmailTemplate(models.Model):
    """
    Email template. Used for sending emails after e.g. issue updates.
    """
    subject = models.CharField(maxlength=1024)
    body = models.TextField(maxlength=8192)
    name = models.CharField(maxlength=512)

    def __str__(self):
        return self.name


    def send(self, recipients, issue, **kw):
        """
        Format message and send it.
        """
        from tuit.mail import Mailer
        events = []
        kw['issue']=issue

        if recipients is None:
            return events

        if hasattr(recipients, 'all'):
            recipients=recipients.all()

        if not hasattr(recipients, '__iter__'):
            recipients = [recipients]

        for recipient in recipients:
            kw['recipient']=recipient
            d = ModelDict(kw)
            subject = ("[%s #%d] "% (properties['site_url'],issue.id)).encode('utf-8')
            subject2 = self.subject % d
            subject += subject2

            html = self.body
            # print html
            html = html % d
            if type(html) is str:
                html = html
            else:
                html=html.encode('utf-8')

            plain = html2text(html)
            plain = plain.decode('utf-8')
            #print plain
            
            Mailer.send_email(subject, recipient, plain, html)

            events.append({'field':recipient.email, 
                           'comment':_('Nofified by email')})

        return events

    class Admin: 
        pass

    class Meta:
        ordering = ['name']
        verbose_name_plural = _('email templates')
        verbose_name = _('email template')

class DbLogRecordType(models.Model):
    name = models.CharField(maxlength=64, blank=True, unique=True)
    

class DbLogRecord(models.Model):
    """
    A log item
    """
    record_type = models.ForeignKey(DbLogRecordType)
    lvl = models.IntegerField()
    msg = models.TextField(maxlength=8192)
    log_date = models.DateTimeField(auto_now_add=True)

    @property
    def html_default_columns(self):
        """
        The default columns to show when displaying an issue in a Widget
        """
        return ((_('Event catecory'),'category_name'),(_('Event severity'),'lvl'),(_('Message'),'msg'),(_('Date'),'log_date'))

    def html_row(self, columns):
        """
        Used for widget rendering
        """
        
        res = ""

        for col in columns:
            try:
                res += "<td>" + {
                    'category_name':lambda: self.record_type.name,
                    'lvl':lambda: "%s" % self.lvl,
                    'msg':lambda: self.msg,
                    'log_date':lambda: datetime_format(self.log_date),
                    }[col]() + "</td>"
            except:
                import traceback as tb
                tb.print_exc()
                raise
            
        return "<tr>%s</tr>" % res

    def __init__(self, *arg, **kw):

        if 'name' in kw:
            n = kw['name']
            del kw['name']
            models.Model.__init__(self, *arg, **kw)
            self.name=n
        else:
            models.Model.__init__(self, *arg, **kw)
#        print self.msg

    def __str__(self):
        return self.msg

    def get_name(self):
        return self.record_type.name

    def set_name(self, value):
        t = DbLogRecordType.objects.filter(name=value)
        if t.count() == 0:
            t=DbLogRecordType(name=value)
            t.save()
            self.record_type=t
        else:
            self.record_type=t[0]

    name = property(get_name, set_name)


class Event(models.Model):
    """
    A simple event handler, stored in the db.
    """
    description = models.TextField(maxlength=256)
    event = models.CharField(maxlength=64)
    code = models.TextField(maxlength=8192)

    def __str__(self):
        return self.event +': '+self.description

    def run(event, issue, update, **kw):
        exec event.code.replace('\r','')
        
    @staticmethod
    def fire(name, issue=None, update=None, **kw):
        if not hasattr(name, '__iter__'):
            name=[name]
        for ev in Event.objects.filter(event__in=name):
            ev.run(issue, update, **kw)


    class Admin:
        pass

        
    class Meta:
        ordering = ['event']
        verbose_name_plural = _('scripted events')
        verbose_name = _('scripted event')
        
class UserProfile(models.Model):
    """
    Extra data to store about each user. Django has a bit of automagic
    to tie this up with the main user object.
    """
    user = models.ForeignKey(User, unique=True)
    location = models.TextField(maxlength=512, blank=True)
    building = models.TextField(maxlength=512, blank=True)
    office = models.TextField(maxlength=512, blank=True)
