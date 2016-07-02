# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django import forms
from django.forms.widgets import HiddenInput, RadioSelect,\
    SplitHiddenDateTimeWidget
from django.utils.encoding import force_text
from django.utils.translation import ugettext_lazy as _

from cosinnus.forms.group import GroupKwargModelFormMixin
from cosinnus.forms.tagged import get_form
from cosinnus.forms.user import UserKwargModelFormMixin
from cosinnus.forms.widgets import DateTimeL10nPicker, SplitHiddenDateWidget

from cosinnus_poll.models import Poll, Suggestion, Vote, Comment
from cosinnus.forms.attached_object import FormAttachable


class _PollForm(GroupKwargModelFormMixin, UserKwargModelFormMixin,
                 FormAttachable):
    
    url = forms.URLField(widget=forms.TextInput, required=False)

    class Meta:
        model = Poll
        fields = ('title', 'suggestion', 'from_date', 'to_date', 'note', 'street',
                  'zipcode', 'city', 'public', 'image', 'url')
        widgets = {
            'from_date': SplitHiddenDateWidget,       
            'to_date': SplitHiddenDateWidget,
        }
    
    def clean_to_date(self):
        date = self.cleaned_data['to_date']
        # if no end time was set, always set 23:59 for "end of day"
        if date and not self.data.get('to_date_1', None):
            date = date.replace(hour=23, minute=59)
        return date

    def __init__(self, *args, **kwargs):
        super(_PollForm, self).__init__(*args, **kwargs)
        instance = kwargs.get('instance')
        if instance:
            self.fields['suggestion'].queryset = Suggestion.objects.filter(
                poll=instance)
        else:
            del self.fields['suggestion']


PollForm = get_form(_PollForm)


class SuggestionForm(forms.ModelForm):

    class Meta:
        model = Suggestion
        fields = ('from_date', 'to_date',)


class VoteForm(forms.Form):
    suggestion = forms.IntegerField(required=True, widget=HiddenInput)
    choice = forms.ChoiceField(choices=Vote.VOTE_CHOICES, required=True)

    def get_label(self):
        pk = self.initial.get('suggestion', None)
        if pk:
            return force_text(Suggestion.objects.get(pk=pk))
        return ''
    
    
class PollNoFieldForm(forms.ModelForm):

    class Meta:
        model = Poll
        fields = ()
        
        
class CommentForm(forms.ModelForm):

    class Meta:
        model = Comment
        fields = ('text',)

