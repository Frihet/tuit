from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render_to_response
from django import template
from json import to_json, from_json
from settings import LOGIN_URL
from urllib import quote
import django.contrib.auth.models
import cgi

import logging
#from tuit.ticket.models import DbLogRecord



def tuit_render(name, keys, request):
    keys['css_links']=[{'url':'/static/common/common.css'},
                       {'url':'/static/jquery-autocomplete/jquery.autocomplete.css'},
                       {'url':"/static/tuit.css"},
                       {'url':"/static/common/datePicker.css"},
                       {'url':"/static/tuit-print.css", 'media':"print"}]
    
    keys['js_links'] = ["/static/common/jquery.js",
                        "/static/common/common.js",
                        "/static/common/static/date.js",
                        "/static/tuit.js",
                        "/static/jquery-autocomplete/jquery.autocomplete.js",
                        "/static/common/date.js",
                        "/static/common/jquery.datePicker.js",
                        "/static/common/tiny_mce/tiny_mce.js",
                        "/tuit/ticket/i18n.js",
                        ]
    keys['user']=request.user

    def js_date_format(python_format):
        for (old,new) in (('%Y','yyyy'),('%m','mm'),('%d','dd')):
            python_format = python_format.replace(old, new)
        return python_format

    keys['js_date_format'] = js_date_format(properties['date_format']);

    return render_to_response(name, keys)

class ModelWrapper:
    def __init__(self, model, dictionary):
        self.__model = model
        self.__dictionary = dictionary


    def __getattr__(self, name):
        if name in self.__dictionary:
            return self.__dictionary[name]
        return getattr(self.__model, name)


class ModelDict:

    def __init__(self, keys=None):
        if keys is None:
            keys={}
        self.dict = keys


    def __getitem__(self, key):
#        print 'access', key
        obj = self.dict
        for subkey in key.split('.'):
            try:
                if hasattr(obj, '__getitem__') and subkey in obj:
                    obj = obj[subkey]
                else:
                    obj = getattr(obj, subkey)
            except:
                return ""

            if obj is None:
                return ""

        if obj is unicode:
#            print "ModeDict unicode", key
            return obj.encode('utf-8')
        try:
#            print "ModelDict return", key
            print type(obj)
            return str(obj)
        except:
            print "ModelDict error on", key
            print type(obj)
            return obj

#    def __setitem__(self, key, value):
#        self.dict[key]=value


class PropertyHandler:

    data=None

    def __init__(self):
        self.data = None

    def __load(self):
        from tuit.ticket.models import Property
        if self.data is None:
            def str_deep(item):
                if type(item) is unicode:
                    return item.encode('utf-8')
                if hasattr(item, 'iteritems'):
                    res = {}
                    for i in item:
                        res[i.encode('utf-8')] = str_deep(item[i])
                    return res
                if hasattr(item,'__iter__'):
                    res=[]
                    for i in item:
                        res.append(str_deep(i))
                return item


            self.data=dict(map(lambda x: (x.name, str_deep(from_json(x.value))), Property.objects.all()))

    def __getitem__(self, name):
        self.__load()
#        print self.data
        return self.data[name]

    def __setitem__(self, name, value):
        self.__load()
        from tuit.ticket.models import Property

        if name in self.data:
            p=Property.objects.get(name=name)
            p.value=to_json(value)
            p.save()
        else:
            Property(name=name, value=to_json(value)).save()
        self.data[name] = value;

#    def __getattr__(self, name):
#        if name in ['data']:
#            raise AttributeError()
#        self.load()
#        if name not in self.data:
#            raise AttributeError()
#        return self.data[name]

properties = PropertyHandler()

class DbHandler(logging.Handler):
    
    def __init__(self):
        # Log all events, we filter them when viewing them instead
        logging.Handler.__init__(self) 
       
    def emit(self, record):
        from tuit.ticket.models import DbLogRecord
        r = DbLogRecord(name=record.name or "",
                        lvl=record.levelno or 0,
                        msg = record.getMessage())
        r.save()
                        
def log_init():    
    logging.getLogger().addHandler(DbHandler())
    logging.getLogger().setLevel(1)


def email_valid(emailkey):
    """Email validation, checks for syntactically invalid email
    courtesy of Mark Nenadov.
    See
    http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/65215"""
    import re
    emailregex = "^.+\\@(\\[?)[a-zA-Z0-9\\-\\.]+\\.([a-zA-Z]{2,3}|[0-9]{1,3})(\\]?)$"
    if len(emailkey) > 7:
        if re.match(emailregex, emailkey) != None:
            return True
        return False
    else:
        return False


def login_required(view_func):
    """
    Decorator for views that checks whether a user has a particular permission
    enabled, redirecting to the log-in page if necessary.
    """
    def _checklogin(request, *args, **kwargs):
        if request.user.is_authenticated():
            return view_func(request, *args, **kwargs)
        return HttpResponseRedirect('%s?%s=%s' % (LOGIN_URL, 'next', quote(request.get_full_path())))
    return _checklogin


def escape_recursive(*arg):
    if len(arg) == 0:
        return tuple()
    if len(arg) == 1:
        return escape_recursive_internal(arg[0])
    return escape_recursive_internal(arg)


def escape_recursive_internal(obj):
    """
    Recursively CGI-escape a set of objects. Can handle strings,
    unicode strings, list-like and dict-like objects. Always returns a
    tuple for tuple input.
    """
    if type(obj) is str:
        return cgi.escape(obj)
    if type(obj) is int:
        return str(obj)
    if type(obj) is unicode:
        return cgi.escape(obj.encode('utf-8'))
    if hasattr(obj,'iteritems'):
        return dict(map(lambda (x,y): (escape_recursive(x),escape_recursive(y)), obj.iteritems()))
    if type(obj) is tuple:
        return tuple(map(escape_recursive, obj))
    if hasattr(obj,'__iter__'):
        return map(escape_recursive, obj)

    return None
    

def encode_recursive(*arg):
    if len(arg) == 0:
        return tuple()
    if len(arg) == 1:
        return encode_recursive_internal(arg[0])
    return encode_recursive_internal(arg)


def encode_recursive_internal(obj):
    """
    Recursively CGI-escape a set of objects. Can handle strings,
    unicode strings, list-like and dict-like objects. Always returns a
    tuple for tuple input.
    """
    if type(obj) is str:
        return obj
    if type(obj) is unicode:
        return obj.encode('utf-8')
    if hasattr(obj,'iteritems'):
        return dict(map(lambda (x,y): (encode_recursive_internal(x),encode_recursive_internal(y)), obj.iteritems()))
    if type(obj) is tuple:
        return tuple(map(encode_recursive_internal, obj))
    if hasattr(obj,'__iter__'):
        return map(encode_recursive_internal, obj)
        
    return None
    


log_init()

# Monkey path in the tuit_description field for the regular Django User class
django.contrib.auth.models.User.tuit_description = property(lambda user:"<a href='%s/account/%s'>%s - %s %s</a>" %(properties['site_location'], user.username, user.username, user.first_name, user.last_name))

def check_permission(perm, user):
    if perm == '':
        return True
    if perm == 'is_staff':
        return user.is_staff
    return user.has_perm(perm)

