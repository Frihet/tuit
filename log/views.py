# Create your views here.

from tuit.ticket.models import *
from django.http import *
import datetime
from django.contrib.auth.models import *
from tuit.util import *
from django.utils.translation import gettext as _
import logging
from tuit.home.widget import Widget

def make_select_options(opt, value):
    def make_option(opt_id, opt_desc):
        checked = ""
        if opt_id == value:
            checked = "selected"
        return "<option value='%s' %s >%s</option>" % escape_recursive(opt_id, checked, opt_desc)

    return make_option("", _("All")) + "\n".join(map(lambda x:make_option(x.id,x.name),opt))

@login_required
def view(request):
    if not request.user.is_staff:
        return None

    items = DbLogRecord.objects.all().order_by('-log_date')

    min_level = ""
    try:
        min_level = int(request.GET['min_level'])
        items = items.filter(lvl__gte = min_level)
    except:
        pass
    
    record_type=""
    try:
        record_type = int(request.GET['record_type'])
        items = items.filter(record_type = record_type)
    except:
        pass

    record_options = make_select_options(DbLogRecordType.objects.order_by('name'), record_type)
    items = items.order_by('-log_date')
    
    keys={'title': _("Event log"),
          'log_widget': Widget(_('Filtered log'), items,
                               request, 'log',item_count=100,
                               class_names="full_width"),
          'min_level':min_level,
          'record_type':record_type,
          'record_options':record_options}
    
    return tuit_render('log.html', keys, request)

