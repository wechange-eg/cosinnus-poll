# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import django.dispatch as dispatch
from django.utils.translation import ugettext_lazy as _

""" Cosinnus:Notifications configuration etherpad. 
    See http://git.sinnwerkstatt.com/cosinnus/cosinnus-core/wikis/cosinnus-notifications-guidelines.
"""


""" Signal definitions """
poll_created = dispatch.Signal(providing_args=["user", "obj", "audience"])
poll_comment_posted = dispatch.Signal(providing_args=["user", "obj", "audience"])
tagged_poll_comment_posted = dispatch.Signal(providing_args=["user", "obj", "audience"])
voted_poll_comment_posted = dispatch.Signal(providing_args=["user", "obj", "audience"])


""" Notification definitions.
    These will be picked up by cosinnus_notfications automatically, as long as the 
    variable 'notifications' is present in the module '<app_name>/cosinnus_notifications.py'.
    
    Both the mail and subject template will be provided with the following context items:
        :receiver django.auth.User who receives the notification mail
        :sender django.auth.User whose action caused the notification to trigger
        :receiver_name Convenience, full name of the receiver
        :sender_name Convenience, full name of the sender
        :object The object that was created/changed/modified and which the notification is about.
        :object_url The url of the object, if defined by get_absolute_url()
        :object_name The title of the object (only available if it is a BaseTaggableObject)
        :group_name The name of the group the object is housed in (only available if it is a BaseTaggableObject)
        :site_name Current django site's name
        :domain_url The complete base domain needed to prefix URLs. (eg: 'http://sinnwerkstatt.com')
        :notification_settings_url The URL to the cosinnus notification settings page.
        :site Current django site
        :protocol Current portocol, 'http' or 'https'
        
    
""" 
notifications = {
    'poll_created': {
        'label': _('A user created a new poll'), 
        'mail_template': 'cosinnus_poll/notifications/poll_created.txt',
        'subject_template': 'cosinnus_poll/notifications/poll_created_subject.txt',
        'signals': [poll_created],
        'default': True,
    },  
    'poll_comment_posted': {
        'label': _('A user commented on one of your polls'), 
        'mail_template': 'cosinnus_poll/notifications/poll_comment_posted.html',
        'subject_template': 'cosinnus_poll/notifications/poll_comment_posted_subject.txt',
        'signals': [poll_comment_posted],
        'default': True,
    },    
    'tagged_poll_comment_posted': {
        'label': _('A user commented on a poll you were tagged in'), 
        'mail_template': 'cosinnus_poll/notifications/tagged_poll_comment_posted.html',
        'subject_template': 'cosinnus_poll/notifications/tagged_poll_comment_posted_subject.txt',
        'signals': [tagged_poll_comment_posted],
        'default': True,
    },  
    'voted_poll_comment_posted': {
        'label': _('A user commented on an poll you voted in'), 
        'mail_template': 'cosinnus_poll/notifications/voted_poll_comment_posted.html',
        'subject_template': 'cosinnus_poll/notifications/voted_poll_comment_posted_subject.txt',
        'signals': [voted_poll_comment_posted],
        'default': True,
    },  
}
