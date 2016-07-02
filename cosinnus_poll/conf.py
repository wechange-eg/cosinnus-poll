# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.conf import settings  # noqa
from appconf import AppConf


class CosinnusPollConf(AppConf):
    # identifier for token label used for the poll-feed token in cosinnus_profile.settings 
    TOKEN_EVENT_FEED = 'poll_feed'
    
    # should the calendar view load *all* polls, even past ones? 
    # can be very DB intensive for groups with many polls
    CALENDAR_ALSO_SHOWS_PAST_EVENTS = False
    