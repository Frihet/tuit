# Create your views here.

from tuit.util import *

def index(request):
    return tuit_render('admin/tuitadmin.html', {}, request)
