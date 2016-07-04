# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.conf.urls import patterns, url


cosinnus_group_patterns = patterns('cosinnus_poll.views',
    url(r'^$', 'index_view', name='index'),

    url(r'^list/$', 'poll_list_view', name='list', kwargs={'poll_view': 'current'}),
    url(r'^list/past/$', 'poll_list_view', name='list_past', kwargs={'poll_view': 'past'}),
    url(r'^add/$', 'poll_add_view',  {'form_view': 'add'},  name='add'),
    url(r'^(?P<slug>[^/]+)/$', 'poll_vote_view', {'form_view': 'edit'},  name='detail'),
    url(r'^(?P<slug>[^/]+)/edit/$', 'poll_edit_view', {'form_view': 'edit'}, name='edit'),
    url(r'^(?P<slug>[^/]+)/delete/$', 'poll_delete_view', {'form_view': 'delete'}, name='delete'),
    url(r'^(?P<slug>[^/]+)/complete/$', 'poll_complete_view', name='complete', kwargs={'mode': 'complete'}),
    url(r'^(?P<slug>[^/]+)/complete/(?P<option_id>\d+)/$', 'poll_complete_view', name='complete', kwargs={'mode': 'complete'}),
    url(r'^(?P<slug>[^/]+)/reopen/$', 'poll_complete_view', name='reopen', kwargs={'mode': 'reopen'}),
    url(r'^(?P<slug>[^/]+)/archive/$', 'poll_complete_view', name='archive', kwargs={'mode': 'archive'}),

    url(r'^(?P<poll_slug>[^/]+)/comment/$', 'comment_create', name='comment'),
    url(r'^comment/(?P<pk>\d+)/$', 'comment_detail', name='comment-detail'),
    url(r'^comment/(?P<pk>\d+)/delete/$', 'comment_delete', name='comment-delete'),
    url(r'^comment/(?P<pk>\d+)/update/$', 'comment_update', name='comment-update'),
)


cosinnus_root_patterns = patterns(None)
urlpatterns = cosinnus_group_patterns + cosinnus_root_patterns
