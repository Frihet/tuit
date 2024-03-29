# Create your views here.

from django.contrib.auth.models import *
from tuit.util import *
#import re
from django.utils.translation import gettext as _
import tuit.settings 

def help(request):
    try:
        return tuit_render("help.%s.html" % tuit.settings.LANGUAGE_CODE, {'title':_('Help')}, request)
    except:
        return tuit_render('help.html', {'title':_('Help')}, request)

def help_page(request, page):
    try:
        return tuit_render("%s.%s.html" % (page, tuit.settings.LANGUAGE_CODE), {'title':_('Help')}, request)
    except:
        return tuit_render('%s.html' % page, {'title':_('Help')}, request)

