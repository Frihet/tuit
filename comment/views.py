# Create your views here.

from tuit.json import to_json
from tuit.comment.models import *
#from django.http import *
#import datetime
#from django.contrib.auth.models import User
from tuit.util import *
#import re
#from django.utils.translation import gettext as _
import logging


@login_required
def get(request):
    if not request.user.has_perm('comment.add_comment'):
        comments = False
    else:
        comments = map(lambda c: c.dict, Comment.objects.filter(url=request.GET['url'].rstrip('/')))

    res = HttpResponse(mimetype='application/x-javascript')
    res.write(to_json(comments))
    return res


@login_required
def set(request):

    if not request.user.has_perm('comment.add_comment'):
        ok = False
    else:
        ok = True
        try:
            url=request.GET['url'].rstrip('/')
            text = request.GET['comment']
            if text == '':
                raise 'error'
            user = request.user
            comment = Comment(text=text, user=user, url=url)
            comment.save()
        except:
            ok = False

    res = HttpResponse(mimetype='application/x-javascript')
    res.write(to_json(ok))
    return res
