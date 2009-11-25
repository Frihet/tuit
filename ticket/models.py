from django.db import models
from django.contrib.auth.models import *
from django.utils.html import strip_tags
from tuit.html2text import html2text
from tuit.util import ModelDict, properties
from django.utils.translation import gettext as _
from tuit.json import to_json, from_json
from tuit.util import email_valid, escape_recursive, encode_recursive
from tuit.ticket.templatetags.tuit_extras import datetime_format, date_format
# Import email handling stuff for email templates
import smtplib
import email.mime.text
import email.mime.multipart
import re
import cgi

def N_(str):
    return str

def format_user(u):
    if u:
        return "%s - %s %s" % (u.username, u.first_name, u.last_name)
    return ""

def get_user(name):
    try:
        uname = name.split(' ')[0]
        return User.objects.get(username=uname)
    except User.DoesNotExist:
        return None

def get_issue(name):
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


class Status(models.Model):
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

    def __str__(self):
        return self.format

    class Admin:
        pass

    class Meta:
        ordering = ['name']
        verbose_name_plural = _('external contacts')
        verbose_name = _('external contact')
        

class CiDependency(models.Model):
    issue = models.ForeignKey("Issue")
    ci_id = models.IntegerField()
    description = models.CharField(maxlength=512)
    view_order = models.IntegerField()

    class Meta:
        unique_together = (('issue','ci_id'),)

class Issue(models.Model):
    current_status = models.ForeignKey(Status)
    type = models.ForeignKey(IssueType)
    category = models.ForeignKey(Category)
    assigned_to = models.ForeignKey(User, null=True, blank=True, related_name='assigned')
    co_responsible = models.ManyToManyField(User, related_name='co_responsible_for')
    cc_user = models.ManyToManyField(User, related_name='cc_on')
    cc_contact = models.ManyToManyField(Contact, related_name='cc_on')
    requester = models.ForeignKey(User, related_name='requested')
    subject = models.CharField(maxlength=256)
    description = models.CharField(maxlength=8192)
    impact = models.IntegerField()
    urgency = models.IntegerField()
    creation_date = models.DateTimeField(auto_now_add=True)
    dependencies = models.ManyToManyField('self', symmetrical=False, related_name='dependants')
    create_description = models.CharField(maxlength=8192)
    creator = models.ForeignKey(User, related_name='created')

    location = models.CharField(maxlength=256, blank=True)
    building = models.CharField(maxlength=256, blank=True)
    office = models.CharField(maxlength=256, blank=True)

    __errors={}
    __extra_fields = None
    __ci_dependencies = None
    # Dummy variable needed to get some searches working - never use it for anything!!!
    priority_placeholder=None

    @property
    def html_default_columns(self):
        return ((_('Issue name'),'name'),(_('Priority'),'priority'),(_('Requester'),'requester'))

    @property
    def extra_fields(self):
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
        models.Model.save(self)
        for i in self.extra_fields:
            i.value.issue=self
            i.value.save()

    @property
    def has_location(self):
#        print self.type.has_location
        return self.type.has_location

    @property
    def html(self):
        return "<a href='%s'>%d - %s</a>" % (self.url_internal,self.id, self.subject)

    def html_row(self, columns):
        res = ""

        for col in columns:
            res += self.html_cell(col)
            
        return "<tr>%s</tr>" % res

    def html_cell(self, col):
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
            print 'Issue.html_cell failed while fetching column', col,'for issue',self.id
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
#                print "Assign value ", values[el], 'to', el
                new = values[el]
                if old[el] != new:
                    events.append({'field':el, 'old':old[el], 'new':new})
                    setattr(self, el, values[el])

#        if self.id:
#            self.save_ci_ids()
        
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
                        print 'EMPTY VALUE'
                        self.error(el.field.name, _('This field is required.'))
            elif not el.field.blank:
                print 'NO VALUE', el.field.name
                print 'IN', values
                self.error(el.field.name, _('This field is required.'))

        return events

    def error(self, name, msg):
        if name not in self.__errors:
            self.__errors[name]=[]
        self.__errors[name].append(msg)

    def set_current_status_string(self, value):
        #print 'try'
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
#        else:
#            print 'requester is', u.username
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
            print 'TRALALA'
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
#        print 'lalala'#, all
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
        if name[0] == '_':
            raise AttributeError()
                
#        print 'Accessing', name
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
            ('view_internal', 'Can view internal updates'),
            )
    

class IssueField(models.Model):
    FIELD_TYPE_CHOICES = (
        ('text',_('Text field')),
        ('grading',_('Grade from 1 to 5')),
        ('dropdown',_('Dropdown box')),
        ('textarea',_('Multiline text area')),
        ('date',_('Date')),
        )

    name = models.CharField(maxlength=64)
    short_description = models.CharField(maxlength=64)
    long_description = models.CharField(maxlength=256)
    field_type = models.CharField(maxlength=16, choices=FIELD_TYPE_CHOICES)
    blank = models.BooleanField()
    view_order = models.IntegerField()

    def __str__(self):
        return self.short_description

    def render_input(self, data):
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
        return escape_recursive(data.value)

    class Admin: 
        pass

    class Meta:
        ordering = ['short_description']
        verbose_name_plural = _('Extra fields for issues')
        verbose_name = _('Extra field for issues')
       

class IssueFieldDropdownItem(models.Model):
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
    issue = models.ForeignKey(Issue)                          
    field = models.ForeignKey(IssueField)                     
    item = models.ForeignKey(IssueFieldDropdownItem)                     

class IssueFieldValue(models.Model):                          
    issue = models.ForeignKey(Issue)                          
    field = models.ForeignKey(IssueField)                     
    value = models.CharField(maxlength=8192)                  
   
class IssueUpdate(models.Model):
    user = models.ForeignKey(User,null=True,blank=True)
    contact = models.ForeignKey(Contact,null=True,blank=True)
    comment = models.CharField(maxlength=8192)
    description = models.CharField(maxlength=8192)
    creation_date = models.DateTimeField(auto_now_add=True)
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
    def html_default_columns(self):
        return ((_('Issue name'),'name'),(_('Update'),'update'),(_('Priority'),'priority'),(_('Requester'),'requester'),(_('Update date'),'creation_date'))

    def html_row(self, columns):
        res = ""

        for col in columns:
            try:
                if col == 'update':
                    def remove_html_tags(data):
                        import re
                        p = re.compile(r'<.*?>')
                        return p.sub('', data)
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
    update = models.ForeignKey(IssueUpdate)
    name = models.CharField(maxlength=8192)
    filename = models.CharField(maxlength=8192)
    mime = models.CharField(maxlength=128)

    @property
    def url(self):
        return properties['site_url'] + properties['site_location'] + '/ticket/attachment/%d/%s' % (self.id, self.name)


    
#    def __init__(self, issue, status, user, comment, **kw):
#        super(IssueUpdate, self).__init__()
#        issue.status = status
#        self.comment = comment
#        self.user = user
#        self.description = ""

#        for key, value in kw.iteritems():
#            field = IssueField.objects.get(name=key)
#            if value != getattr(issue,field.name):
#                IssueFieldValue(issue=issue, field=field, value=value)
#                description += ("<p>Updated field %s</p>" % (field,))

class IssueFieldValue(models.Model):
    # The issue that is updated
    issue = models.ForeignKey(Issue)
    # The field that is updated
    field = models.ForeignKey(IssueField)
    # The new value
    value = models.CharField(maxlength=64)


class Property(models.Model):
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
    subject = models.CharField(maxlength=1024)
    body = models.TextField(maxlength=8192)
    name = models.CharField(maxlength=512)

    def __str__(self):
        return self.name


    def send(self, recipients, issue, **kw):
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
    record_type = models.ForeignKey(DbLogRecordType)
    lvl = models.IntegerField()
    msg = models.TextField(maxlength=8192)
    log_date = models.DateTimeField(auto_now_add=True)

    @property
    def html_default_columns(self):
        return ((_('Event catecory'),'category_name'),(_('Event severity'),'lvl'),(_('Message'),'msg'),(_('Date'),'log_date'))

    def html_row(self, columns):
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
    user = models.ForeignKey(User, unique=True)
    location = models.TextField(maxlength=512, blank=True)
    building = models.TextField(maxlength=512, blank=True)
    office = models.TextField(maxlength=512, blank=True)
