# Misc utility functions for tuit
# -*- coding: utf-8 -*-

from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render_to_response
from django import template
from tuit.json import to_json, from_json
from tuit.settings import LOGIN_URL
from urllib import quote
from django.db import models
import django.contrib.auth.models
import cgi
import time
import re
import datetime
import random
import string
import simplejson
import datetime

import logging

def model_to_json(obj):
    cls = type(obj)
    res = dict((field.name, getattr(obj, field.name))
               for field in cls._meta.fields)
    res["__jsonclass__"] = [cls.__module__ + '.' + cls.__name__, []]
    print res
    return res

models.Model.__to_json__ = model_to_json

class JsonObjEncoder(simplejson.JSONEncoder):
     def default(self, obj):
         if hasattr(obj, '__to_json__'):
             return obj.__to_json__()
         elif isinstance(obj, (datetime.datetime, datetime.date)):
             return str(obj)
         #return {'__type_error__': repr(obj) + " is not JSON serializable"}
         raise TypeError(repr(obj) + " is not JSON serializable")

def tuit_render(name, keys, request):
    """
    Add common rendering keys like various js and css links and call render_to_response
    """

    from tuit.home.widget import Widget
    from tuit.ticket.models import IssueUpdate

    keys['css_links']=[{'url':"/static/tuit.css"},
                       {'url':'/static/jquery-autocomplete/jquery.autocomplete.css'},
                       {'url':"/static/common/datePicker.css"},
                       {'url':"/static/tuit-print.css", 'media':"print"}]
    
    keys['js_links'] = ["/static/common/jquery.js",
                        "/static/common/common.js",
                        "/static/tuit.js",
                        "/static/jquery-autocomplete/jquery.autocomplete.js",
                        "/static/common/date.js",
                        "/static/common/jquery.datePicker.js",
                        "/static/common/tiny_mce/tiny_mce.js",
                        "/tuit/ticket/i18n.js",
                        ]
    keys['application'] = 'FreeTIL'
    keys['user']=request.user
    keys['counter'] = "%.4f" % time.time()
    if 'foswiki_url' not in properties:
        properties['foswiki_url'] = '/cgi-bin/foswiki/'

    keys['foswiki_url'] = properties['foswiki_url']

    last_updates = IssueUpdate.objects.order_by('-creation_date').filter(user=request.user).distinct('issue_id')
    keys['recent_updates'] = Widget(_('Latest updates'),
                                    last_updates, request, 'my_updates',class_names='widget_2',
                                    style='list',
                                    columns = (('update','update'),))


    def js_date_format(python_format):
        for (old,new) in (('%Y','yyyy'),('%m','mm'),('%d','dd')):
            python_format = python_format.replace(old, new)
        return python_format

    keys['js_date_format'] = js_date_format(properties['date_format']);

    if 'widgets' in keys:
        keys['widgets_by_name'] = dict((widget.slug, widget) for widget in keys['widgets'])

    if 'application/json' in request.META.get('HTTP_ACCEPT', '') or request.GET.get('_HTTP_ACCEPT', '') == 'application/json':
        data = keys
        selector = request.GET.get('_json_selector', '')
        if (selector):
            selector = simplejson.loads(selector)
            used_selector = []
            for key in selector:
                try:
                    data = data[key]
                except Exception:
                    try:
                        data = getattr(data, key)
                    except Exception:
                        raise Exception("Bad key in selector after %s: %s not in %s" % (simplejson.dumps(used_selector), key, simplejson.dumps(data, cls=JsonObjEncoder)))
                used_selector.append(key)

        return HttpResponse(simplejson.dumps(data, cls=JsonObjEncoder),
                            mimetype='application/json')
    return render_to_response(name, keys)

class ModelWrapper:
    """
    A wrapper to place around a model with an extra dict to place overrides for attribute values in
    """
    def __init__(self, model, dictionary):
        self.__model = model
        self.__dictionary = dictionary


    def __getattr__(self, name):
        if name in self.__dictionary:
            return self.__dictionary[name]
        return getattr(self.__model, name)


class ModelDict:
    """
    A dict that makes a model or dict have hierarchical keys,
    e.g. "issue.user.username" becomes tha name of a key. Only
    supports attibute access.
    """
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
#            print type(obj)
            return str(obj)
        except:
            print "ModelDict error on", key
#            print type(obj)
            return obj

#    def __setitem__(self, key, value):
#        self.dict[key]=value

properties = None

class PropertyHandler(object):
    """
    A loader/saver thingiee for ticket.model.Property lines
    """
    data=None

    def __new__(cls):
        global properties
        if properties is None:
            properties = object.__new__(cls)
        return properties

    def process_request(self, request):
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

            self.data=dict(map(lambda x: (x.name, encode_recursive(from_json(x.value))), Property.objects.all()))

    def __contains__(self, name):
        self.__load()
        return name in self.data

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
    """
    A logging.Handler implementation that uses the ticket.models.DbLogRecord
    """

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


def date_valid(datestr):
    try:
        return datetime.datetime.strptime(datestr, properties['date_format'])
    except:
        
        return False


def email_valid(emailkey):
    """
    Email validation, checks for syntactically invalid email
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
    """
    Performs cgi.escape recursively on lists, tuples, dicts, etc of
    items. Also converts unicode objects to utf-8 encoded regular
    strings.
    """
    if len(arg) == 0:
        return tuple()
    if len(arg) == 1:
        return escape_recursive_internal(arg[0])
    return escape_recursive_internal(arg)


def escape_recursive_internal(obj):
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
    """
    Performs unicode object to utf-8 string conversion recurseivlely.
    """
    if len(arg) == 0:
        return tuple()
    if len(arg) == 1:
        return encode_recursive_internal(arg[0])
    return encode_recursive_internal(arg)


def encode_recursive_internal(obj):
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
        
    return obj
    


log_init()

# Monkey path in the tuit_description field for the regular Django User class
django.contrib.auth.models.User.tuit_description = property(lambda user:"<a href='%s/account/%s'>%s - %s %s</a>" %(properties['site_location'], user.username, user.username, user.first_name, user.last_name))

def check_permission(perm, user):
    """
    Checks if the specified user has the specified permission, which
    may also be is_staff for checking if the user has the staff flag
    set.
    """
    if perm == '':
        return True
    if perm == 'is_staff':
        return user.is_staff
    return user.has_perm(perm)


def generate_password(length=8, chars=string.letters + string.digits):
    return ''.join(random.choice(chars) for i in xrange(length))
