'''
Created on 05.08.2014

@author: Sascha
'''
from django.utils.translation import ugettext_lazy as _

from cosinnus.views.mixins.filters import CosinnusFilterSet
from cosinnus.forms.filters import AllObjectsFilter, SelectCreatorWidget
from cosinnus_poll.models import Poll


class PollFilter(CosinnusFilterSet):
    creator = AllObjectsFilter(label=_('Created By'), widget=SelectCreatorWidget)
    
    class Meta:
        model = Poll
        fields = ['creator']
        order_by = (
            ('-created', _('Newest Created')),
            ('title', _('Title')),
        )
    
    def get_order_by(self, order_value):
        return super(PollFilter, self).get_order_by(order_value)
    