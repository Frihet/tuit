#!/usr/bin/python
# -*- coding: utf-8 -*-

from django.core.management import setup_environ
try:
    import settings # Assumed to be in the same directory.
except ImportError:
    import sys
    sys.stderr.write("Error: Can't find the file 'settings.py' in the directory containing %r. It appears you've customized things.\nYou'll have to run django-admin.py, passing it your settings module.\n(If the file settings.py does indeed exist, it's causing an ImportError somehow.)\n" % __file__)
    sys.exit(1)

project_directory = setup_environ(settings)

from tuit.ticket.models import *
from django.contrib.auth.models import *
import random

random.seed()
sd_group = None
other_group = None
other_users = []
sd_users = []

def random_element(lst):
    if not len(lst):
        return None
    return lst[random.randint(0,len(lst)-1)]

def random_location():
    return random_element(('Bergen','Oslo','Trondheim','Tromsø',''))

def random_building():
    return random_element(('Stora huset','Smittskyddslabbet','Immunologen',''))

def random_name():
    f = random_element(('bo','orvar','tord','amalia','jenny','arno','bernt','torgny','gertrud','brynhilda','ragnhild','benny','bruno','timmy','dagny','malin','märta','maja','kajsa','maria','magdalena','elisabet','gustav','carl','jörgen','rullgardina','viktualia','petronella','hermes','lisbeth','trygvar','harpo','elmhult','ångest'))
    l = random_element(('svensson','johansson','lingongren','aktersvans','rödbeta','rosenklimp','långstrump','appelkvist','kvarnskaft','svartfot','sidenstolpe','andersson','nilsson','persson','petterson','elmhult','camenbert','långfot','gren','ek','hed','träsk','lillsjö','edensjö','luddfot','luddenberg','fluffencrans','fluffenberg','fikonberg','fikonfot','appelskrutt','rosenklimp','gulleklimp','appelklimp','akterklimp','fikonklimp','rosenskrott','akterskrott','lingonfot','lingonklimp','lingonberg','tannenfot','tannenben','tannenfjant','långben','akterben','lingonkvist','svartkvist','fikonkvist'))
    return (f,l)

def to_ascii(str):
    return str.replace("ö","o").replace("ä","a").replace("å","a")


def create_user_data():
    sd_group = Group(name='sd')
    sd_group.save()
    other_group = map(lambda n:Group(name=n),('Labpersonal','Elever','Smittolabbet'))
    map(lambda g:g.save(), other_group)

    for (un, first, last, email) in (('jon','Jon','Johansen','JonRoy.Johansen@fhi.no'),
                                     ('line','Line','Halvorsen','line.halvorsen@fhi.no'),
                                     ('axel','Axel','Liljencrantz','axel.liljencrantz@freecode.no'),
                                     ('admin','Admin','Adminsson','axel.liljencrantz@freecode.no'),
                                     ('brynjar','Brynjar','Svalbardsen','brynjar@example.com'),
                                     ('lorry','Lorentz','Gudmundsen','lorry@example.com')):
        u = User(username=un, first_name=first, last_name=last, email=email,password='sha1$32ecf$347ce5abb5cc70ac9d23d8c11ee6d37cab3c04a1')
        u.save()
        u.groups.add(sd_group)
        u.is_staff = True
        u.is_superuser = True
        u.save()
#        print u.id
        p = UserProfile(user=u, location="fhi", building="Stora huset", office="5",telephone='12345',mobile='23456',pc='69')
        p.save()
        sd_users.append(u)
    print 'SD created'

    used = set()
    for (f,l) in map(lambda x: random_name(), range(1000)):
        un = f
        idx = 1
        while un in used:
            un = f + str(idx)
            idx += 1
        used.add(un)
        fa = to_ascii(f)
        la = to_ascii(l)
        u = User(username=un, first_name=f.capitalize(), last_name=l.capitalize(), email="%s.%s@example.com"%(fa,la),password='sha1$32ecf$347ce5abb5cc70ac9d23d8c11ee6d37cab3c04a1')
        u.save()
        u.groups.add(random_element(other_group))
        u.save()
        p = UserProfile(user=u, location=random_location(), building=random_building(), office=str(random.randint(1,200)),telephone='12345',mobile='23456',pc='69')
        p.save()
        other_users.append(u)
    print 'Users created'


create_user_data()

types = list(IssueType.objects.all())
statuses = list(Status.objects.all())
categorys = list(Category.objects.all())

def random_category():
    return random_element(categorys)

def or_none(el, prob=0.5):
    if random.random() > prob:
        return el
    return None

def random_user():
    return random_element(other_users)

def random_sd():
    return random_element(sd_users)


def random_contact():
    (f,l) = random_name()
    fa = to_ascii(f)
    la = to_ascii(l)
    return make_contact("%s %s <%s.%s@example.com>" % (f.capitalize(), l.capitalize(), fa, la))

def random_person(capitalised):
    res = random_element(('user','luser','somebody','a giraffe','my boss','the company','our supplier','she','he','her boss','the babysitter','the dog','the cat','Larry','Moe','a computer','aliens','crab people','the nanny','Charles','a random power surge','Spider man','the water guy','an octopus','an antilope','a crocodile','Trogdor','my mother','the server room','the janitor','the night watch'))
    if capitalised:
        res=res.capitalize()
    return res

def random_object():
    return random_element(('the phone','the computer','a laptop','the mail server','my lawn mower','the pencil','the couch','an asparagus','a hot potatoe','a fork','the book','the plow','a sword','an abacus','a speedo','the carpet','my chair','the small table','a large bench','the web server','Spartacus','a bucket','a stool','a cage','the ladder','the plant','a flower','my lupines','the garden','the web site','the web cache','a chart','a diagram','a printout','the imaging device','the bucket'))

def random_quality():
    return random_element(('while skiing','on the carpet', 'in the shower','on tuesday','from the future','in space','during a sandstorm','during a power surge','under the couch' ,'by design','on purpose','under the sea','in flagrant violation of common sensibilities','during the shooting of a movie','while killing a rat','while stomping on a cardboard box','while doing the laundry', 'while doing the dishes','while eating pie','while baking cake','while sewing curtains','while captioning a cat','while eating dorritos','while eating burritos'))

def random_action():
    return random_element(('ate','crashed','lost','found','broke','gave away','slapped','defenestrated','humiliated','boarded','stepped on','coudn\'t find','couldn\'t start','stopped','halted','made fun of'))

def random_outcome():
    return random_element(('dry rashes','severe outages','major loss of power','missed meetings','sad pandas','arbitrary soccer goals','fires','axe rampages','minor chafing','undulations in my aura','hail storms','murderous rampages','blogging','microformats','glitches in the matrix','swamp gas','hair loss','stack overflow','hamstergeddon','brain noise','fart noises','apple pie shortage','spontaneous singing','time travel','a sugar surplus','car pooling','fat reduction','clutter','smoking','cancer','excessive sweating','epic win','fansubs','statistics','smoking guns','burnination','a glitch in the Matrix','minor explotions','gun fire','mass displacement'))

def random_subject():
    return "%s %s %s %s" % (random_person(True),
                            random_action(),
                            random_object(),
                            random_quality()
                            )

def random_description():
    return "<p>User is having %s because %s %s %s %s. This has caused %s and needs to %s.</p><p>Please deal with this %s.</p>" % (
        random_element(('a problem','an issue','a fit')),
        random_person(False),
        random_action(),
        random_object(),
        random_quality(),
        random_outcome(),
        random_element(('be fixed','continue','be photgraphed','be discussed','be investigated further','be on the Internet','be televised','stop','be prevented','be made into a kung fu movie','be made fun of','be preserved','be ridiculed','be snorted','happen more often','change')),
        random_element(('now','yesterday','when you feel like it','when the cows come in','whenever','in the future','last week','on thursdays','on sundays','next christmas','next easter','on monday','befor the end of the month','before anybody notices','in due time')),
        )

def random_update():
    return "<p>%s %s and I %s the user is having this problem because %s %s %s %s. This has caused %s and needs to %s.</p>" % (
        random_element(('I have','We have','My team has','The guys have','Our supplier has','The aliens')),
        random_element(('think','suspect','have the feeling that','have come to the conclusion that','feel that perhaps','hava a sneaking suspicion that','do declare that','now know that')),
        random_element(('investigated','mulled on this','given this some though','checked','meditated on this')),
        random_person(False),
        random_action(),
        random_object(),
        random_quality(),
        random_outcome(),
        random_element(('be fixed','continue','be photgraphed','be discussed','be investigated further','be on the Internet','happen more often','stop','be reversed')),
                                                                                                                                             )

def random_ci_string():
    els = ('2 - arne','3 - bosse','5 - bengta','6 - beata','7 - brynhilda','8 - bozena','4 - bodil','9 - jon', '11 - Firewall 01','21 - ldap','22 - postgres')
    res = set()
    while random.random() < 0.4:
        el = random_element(els)
        res.add(el)
    return '\n'.join(res)

def random_boolean():
    return random.randint(0,1)==0


old_issues = []
for it in range(3000):
    if it % 100 == 0:
        print 'Created', it, 'issues'
    i = Issue(type=random_element(types))
    data = dict(current_status_string=str(random_element(statuses).id),
                assigned_to_string=or_none(random_element(sd_users).username,0.1),
                requester_string=random_element(other_users).username,
                subject = random_subject(),
                description = random_description(),
                impact_string = str(random.randint(1,5)),
                urgency_string = str(random.randint(1,5)),
                category_string=str(random_category().id),
                ci_string=random_ci_string(),
                change_type="1",
                date_perform='01.01.2010',
                priority="1",
                risk="1",
                consequence="1",
                difficulty="1",
                implementation_plan="Plan! What plan?",
                test_plan="I have a plan!<br/>It involves pancakes.",
                fallback_plan="Run, you fools!",
                evaluation="Nothing to see here, everbody please move along, now.",
                change_status="1",
                change_manager_comment="Do you have those TPS reports I asked for. That would be great.",                
                )

    i.creator=random_element(sd_users)
    events = i.apply_post(data)
    i.create_description='[]'
    err = i.validate()
    if len(err):
        print 'Error', err
        print 'Data', data

        raise "Ajaj"
    try:
        i.save()
    except:
        print data
        raise
    events.extend(i.apply_post(data))
    i.description_data={'type':'web','events':events}
    i.save()

    old_issues.append(i)
    while random.random() < 0.3:
        el = random_element(old_issues)
        if el and el not in set(i.dependencies.all()):
            i.dependencies.add(el)


    while random.random() < 0.3:
        el = random_sd()
        if el and el not in set(i.cc_user.all()):
            i.cc_user.add(el)
            i.save()

    while random.random() < 0.3:
        el = random_contact()
        if el and el not in set(i.cc_contact.all()):
            i.cc_contact.add(el)
            i.save()

    for it2 in range(random.randint(0,6)):
        iu = IssueUpdate(
            comment=random_update(),
            internal = random_boolean(),
            issue = i,
            description_data={},
            )
        if random.random() < 0.1:
            data['current_status_string']=str(random_element(statuses).id)
        if random.random() < 0.1:
            data['impact_string'] = str(random.randint(1,5))
        if random.random() < 0.1:
            data['urgancy_string'] = str(random.randint(1,5))
        if random.random() < 0.1:
            data['category_string']=str(random_category().id)

        events=i.apply_post(data)
        iu.description_data={'type':'web','events':events}

        if random.random() > 0.4:
            iu.user = random_sd()
        if random.random() > 0.25:
            iu.user = random_user()
        else:
            iu.contact = random_contact()

        iu.save()


# Drop old entries
"""
delete from ticket_issuefielddropdownvalue;
delete from ticket_issuefieldvalue ;
delete from ticket_cidependency;
delete from ticket_issueattachment;
delete from ticket_issueupdate;          
delete from ticket_issue_co_responsible;
delete from ticket_issue_cc_user;
delete from ticket_issue_dependencies;
delete from ticket_issue_cc_contact;
delete from ticket_issue;
delete from ticket_contact;
delete from ticket_userprofile;
delete from django_admin_log;
delete from auth_group_permissions;
delete from auth_user_user_permissions;
delete from auth_permission;
delete from auth_user_groups;
delete from auth_message;
delete from auth_user;
delete from auth_group;

"""

# Set more reasonable dates for fake entries
"""
update ticket_issue set current_status_id = 2 where random() < 0.95;
update ticket_issue set creation_date = now() - interval '6 year' * random();
update ticket_issueupdate iu set creation_date = (select creation_date + interval '5 months'*random() from ticket_issue i where i.id = iu.issue_id);
delete from ticket_issueupdate where creation_date > now();

"""

# Drop issue table
"""
drop table ticket_issue_co_responsible cascade;
drop table ticket_issue_cc_user cascade;
drop table ticket_issue_cc_contact cascade;
drop table ticket_issue_dependencies cascade;
drop table ticket_issue cascade;
drop table ticket_contact cascade;
drop table ticket_dblogrecord cascade;
drop table ticket_dblogrecordtype cascade;
drop table ticket_userprofile cascade;
drop table auth_user cascade;
drop table auth_group cascade;
drop table auth_message cascade;
drop table auth_permission cascade;
drop table auth_user_groups cascade;
drop table auth_user_user_permissions cascade;
drop table auth_group_permissions cascade;

"""
