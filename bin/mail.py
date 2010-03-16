#! /usr/bin/python
import os, os.path, sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
os.environ["DJANGO_SETTINGS_MODULE"] = 'tuit.settings'

import django.core.management
import django.db.transaction

import tuit.mail
import logging
import traceback

@django.db.transaction.commit_manually
def handle_mails():
    try:
        m=tuit.mail.MailGW(None)
        m.do_work()
    except:
        django.db.transaction.rollback()
        raise
    else:
        django.db.transaction.commit()

try:
    handle_mails()
except:
    print traceback.format_exc()
    msg = traceback.format_exc()
    logging.getLogger('mail').error('Error while retriving email: %s' % msg)

logging.getLogger('mail').info('Finished email check')
