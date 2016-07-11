# -*- coding: utf-8 -*-
from __future__ import unicode_literals


def register():
    # Import here to prpoll import side effects
    from django.utils.translation import ugettext_lazy as _
    from django.utils.translation import pgettext_lazy

    from cosinnus.core.registries import (app_registry,
        attached_object_registry, url_registry, widget_registry)

    app_registry.register('cosinnus_poll', 'poll', _('Polls'), deactivatable=True)
    attached_object_registry.register('cosinnus_poll.Poll',
                             'cosinnus_poll.utils.renderer.PollRenderer')
    url_registry.register_urlconf('cosinnus_poll', 'cosinnus_poll.urls')
    widget_registry.register('poll', 'cosinnus_poll.dashboard.CurrentPolls')
    
    # makemessages replacement protection
    name = pgettext_lazy("the_app", "poll")
