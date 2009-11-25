# Create your views here.

from django.contrib.auth.models import *
from tuit.util import *
#import re
from django.utils.translation import gettext as _

@login_required
def help(request):
    return tuit_render('help.html', {'title':_('Tuit Help')}, request)
    
