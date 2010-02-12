# Views for the status app of tuit
# -*- coding: utf-8 -*-

from tuit.util import *
from django.utils.translation import gettext as _
from tuit.status.models import Status
import logging

@login_required
def view(request):
    """
    Basic status view - show latest update
    """
    status = Status.objects.order_by('-creation_date')
    text=''
    if status.count() > 0:
        text=status[0].body
    res = HttpResponse()
    res.write(text)
    return res

@login_required
def edit(request):
    """
    Basic status edit - add new status
    """

    if not request.user.is_staff:
        return None
    messages = ''

    if request.method == 'POST' and 'text' in request.POST: 

        try:
            status = Status(body=request.POST['text'])
            status.user = request.user
            status.save()
            messages = _('Status updated')
        except:
           
            messages = _('Unknown error while updating status.')
            try:
                    import traceback as tb
                    msg = tb.format_exc()
                    logging.getLogger('status').error('Failed to update status. Error: %s' % 
                                                      msg)
            except:
                pass

    status = Status.objects.order_by('-creation_date')
    text=''
    if status.count() > 0:
        text=status[0].body
    return tuit_render('status_edit.html', {'text':text,'messages':messages}, request)


