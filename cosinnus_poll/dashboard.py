# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django import forms
from django.template.loader import render_to_string
from django.utils.translation import ugettext_lazy as _

from cosinnus.utils.dashboard import DashboardWidget, DashboardWidgetForm

from cosinnus_poll.models import Poll, upcoming_poll_filter


class UpcomingPollsForm(DashboardWidgetForm):
    amount = forms.IntegerField(label="Amount", initial=5, min_value=0,
        help_text="0 means unlimited", required=False)
    template_name = 'cosinnus_poll/widgets/poll_widget_form.html'
    
    def __init__(self, *args, **kwargs):
        kwargs.pop('group', None)
        super(UpcomingPollsForm, self).__init__(*args, **kwargs)


class UpcomingPolls(DashboardWidget):

    app_name = 'poll'
    form_class = UpcomingPollsForm
    model = Poll
    title = _('Upcoming Polls')
    user_model_attr = None  # No filtering on user page
    widget_name = 'upcoming'
    widget_template_name = 'cosinnus_poll/widgets/poll_widget.html'
    template_name = 'cosinnus_poll/widgets/upcoming.html'
    
    def get_data(self, offset=0):
        """ Returns a tuple (data, rows_returned, has_more) of the rendered data and how many items were returned.
            if has_more == False, the receiving widget will assume no further data can be loaded.
         """
        count = int(self.config['amount'])
        all_upcoming_polls = self.get_queryset().select_related('group').all()
        polls = all_upcoming_polls
        
        if count != 0:
            polls = polls.all()[offset:offset+count]
        
        data = {
            'polls': polls,
            'all_upcoming_polls': all_upcoming_polls,
            'no_data': _('No upcoming polls'),
            'group': self.config.group,
        }
        return (render_to_string(self.template_name, data), len(polls), len(polls) >= count)

    def get_queryset(self):
        qs = super(UpcomingPolls, self).get_queryset()
        return upcoming_poll_filter(qs)
