
from django import template
from django.core.mail import send_mail
from tuit.util import properties
import tuit.json

register = template.Library()

@register.filter
def date_format(value):
    """
    Format a datetime object with the format defined by the date_format property.
    """
#    print 'DOBEDIDO', type(value)
    return value.strftime(str(properties['date_format']))

date_format.is_safe = True

@register.filter
def to_json(value):
    """
    Format input as json
    """
    return tuit.json.to_json(value)

to_json.is_safe = True

@register.filter
def datetime_format(value):
    """
    Format a datetime object with the format defined by the date_format property.
    """
#    print 'DOBEDIDO', type(value)
    return value.strftime(str(properties['datetime_format']))

date_format.is_safe = True

@register.filter
def user_format(value):
    """
    Print out user information in a way that is both human and machine readable.
    """

    if value is None:
        return ""
#    print "LALALA format %s" % value
    if type(value) in [str, unicode]:
        return value
    
    return "%s - %s %s" % (value.username, value.first_name, value.last_name)


user_format.is_safe = False

@register.filter
def description_format(value):
    """
    Print out a table of description items
    """

    if value is None:
        return ""

    if 'events' not in value:
        return ""

    if len (value['events'])==0:
        return ""

    def format_event(ev):
        if 'field' in ev and 'new' in ev:
            return _("%(field)s changed to %(new)s") % ev
        elif 'field' in ev and 'comment' in ev:
            return "%(field)s: %(comment)s" % ev
        else:
            return str(ev)

    return "<a onclick='$(event.target).next().toggle();'>"+_("Toggle details")+"</a><ul style='display:none'>" + ("".join(map(lambda x:"<li>"+format_event(x)+"</li>", value['events']))) + "</ul>"

user_format.is_safe = False


