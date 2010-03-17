# Create your views here.

from tuit.util import *

@login_required
def index(request):
    return tuit_render('admin/tuitadmin.html', {}, request)
