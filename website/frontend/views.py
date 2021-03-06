#!/usr/bin/python
#
# -*- coding: utf-8 -*-
# vim: set ts=4 sw=4 et sts=4 ai:

"""Simple pages."""

# Python imports
import ConfigParser
import datetime
import logging
import ordereddict
import os
import sys
import time
import re
import urllib2
import simplejson as json
from .data import data
from itertools import ifilter, islice
from datetime import datetime, timedelta
import pytz

from bs4 import BeautifulSoup

from django import http
from django.core.cache import cache
from django.shortcuts import render_to_response
from django.views.decorators.cache import cache_page
from django.views.decorators.cache import cache_control

# Our App imports
from common.views.simple import NeverCacheRedirectView
from tracker import models

config_path = os.path.realpath(os.path.dirname(__file__)+"/../..")
if config_path not in sys.path:
    sys.path.append(config_path)
import config as common_config
CONFIG = common_config.config_load()
LOCALIPS = [re.compile(x) for x in CONFIG['config']['localips'] if x]


def group(request, group):
    if not CONFIG.valid(group):
        return NeverCacheRedirectView.as_view(url="/")(request)

    config = CONFIG.config(group)

    template = request.GET.get('template', 'default')
    if not re.match('[a-z]+', template):
        return NeverCacheRedirectView.as_view(url="/")(request)
    elif template == 'default':
        template = "group"
        # Is the request coming from the room?
        for ipregex in LOCALIPS:
            if ipregex.match(request.META['HTTP_X_REAL_IP']):
                template = 'inroom'
                break

    screenstr = request.GET.get('screen', 'False')
    if screenstr.lower()[0] in ('y', 't'):
        screen = True
    else:
        screen = False

    return render_to_response('%s.html' % template, locals())


def index(request, template="index"):
    groups = ordereddict.OrderedDict()
    #for group in sorted(CONFIG.groups()):
    # Hardcoded for order.
    for group in ('mission', 'america', 'ab', 'cd', 'ef', 'gh'):
        groups[group] = CONFIG.config(group)

    config = CONFIG['config']
    default = CONFIG['default']
    return render_to_response('%s.html' % template, locals())


@cache_control(must_revalidate=True, max_age=600)
def schedule(request):
    """Get the json schedule from LCA and put it in our domain so we can AJAX it."""
    response = http.HttpResponse(content_type='text/javascript')

    schedule = cache.get('schedule')
    if not schedule:
        schedule = urllib2.urlopen('https://us.pycon.org/2012/schedule/json').read()
        cache.set('schedule', schedule, 120)
    response.write(schedule)
    return response

def get_current_next(group, howmany=2):
    if group in data:
        tz = pytz.timezone('US/Pacific')
        now = str(datetime.now(tz))
        return islice(
            ifilter(
                lambda x: x['end'] > now,
                data[group]
            ),
            howmany
        )
    else:
        return []

def json_feed(request, group):
    response = http.HttpResponse(content_type='text/javascript')
    two_elements = list(get_current_next(group))

    for index, element in enumerate(two_elements):
        element = dict(element)
        for key in ('start', 'end'):
            element[key] = str(element[key])
        two_elements[index] = element

    response.write(json.dumps(two_elements))
    return response
