#! /usr/bin/python
# -*- coding: utf-8 -*-

from __future__ import with_statement

import os, os.path, sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
os.environ["DJANGO_SETTINGS_MODULE"] = 'tuit.settings'

import django.core.management
import django.db.transaction

import logging
import traceback
import re
from django.contrib.auth.models import *

admgrp = Group.objects.filter(name='AdminGroup')
for g in admgrp:
    val = ",".join(map(lambda x:x.username.lower(), g.user_set.all()))
    with open("/var/lib/foswiki/data/Main/AdminGroup.txt") as f:
        content = f.read()

        content = re.sub(r'\* *Set *GROUP *=.*',
               r'* Set GROUP =' + val,
               content)

    with open("/var/lib/foswiki/data/Main/AdminGroup.txt","w") as f:
        f.write(content)


logging.getLogger('foswiki').info('Finished foswiki sync')
