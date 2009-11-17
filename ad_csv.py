
import csv

from django.core.management import setup_environ

try:
    import settings # Assumed to be in the same directory.
except ImportError:
    import sys
    sys.stderr.write("Error: Can't find the file 'settings.py' in the directory containing %r. It appears you've customized things.\nYou'll have to run django-admin.py, passing it your settings module.\n(If the file settings.py does indeed exist, it's causing an ImportError somehow.)\n" % __file__)
    sys.exit(1)

project_directory = setup_environ(settings)

from django.contrib.auth.models import *
from tuit.ticket.models import UserProfile


def read_file(fn):
    f=open(fn,'r')
    rows = f.read().split('\n')
    f.close()
    return rows


def load_file(fn):
    rows = read_file(fn)
    names = map(lambda x: x.lower(), rows[0].split('\t'))
    return filter(lambda x:len(x) >1, map(lambda x: dict(zip(names, x.split('\t'))), rows[1:]))

print 'Loading user data'
current_users = dict(map(lambda x: (x.username,x),User.objects.all()))
#print current_users

users = load_file('ad_csv/ad_users.txt')

print 'Creating users'
for user in users:
    print '.',
    try:
        (first,last) = user['displayname'].split(' ',1)
    except:
#        print 'User data:',user
        (first,last)=(user['displayname'],user['displayname'])
    if user['name'] in current_users:
        u=current_users[user['name']]
        u.first_name=first
        u.last_name=last
        try:
            u.get_profile()
        except:
            p = UserProfile(user=u, location="", building="", office="")
            p.save()
        u.save()
    else:
        u=User(first_name=first, last_name=last, username=user['name'],
               email=user['name']+'@example.com')
        if len(u.username) < 30:
            u.save()
            p = UserProfile(user=u, location="", building="", office="")
            p.save()
            current_users[u.username]=u
        else:
            print 'Username too long, skipping user:', u


current_groups = dict(map(lambda x: (x.name,x),Group.objects.all()))

ug_data = load_file('ad_csv/ad_user_groups.txt')
print 'Creating groups'
for ug in ug_data:
    print '.',
    group_name = ug['cn']
    user_name = ug['name']

    if group_name not in current_groups:
        g=Group(name=group_name)
        g.save()
        current_groups[group_name] = g

    g= current_groups[group_name]
    if user_name not in current_users:
        continue
    u = current_users[user_name]

    u_set = list(g.user_set.all())
    if u not in u_set:
        g.user_set.add(u)

print 'Saving groups. Probably unneeded?'
#for name,g in current_groups.iteritems():
#    print '.',
#    g.save()
