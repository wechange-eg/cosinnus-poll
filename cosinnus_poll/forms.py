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

from cosinnus_poll.models import Poll, Option, Vote, Comment
from cosinnus.forms.attached_object import FormAttachable


class _PollForm(GroupKwargModelFormMixin, UserKwargModelFormMixin,
                 FormAttachable):
    
    # TODO: after form submission, restore initial values on these fields, if active votes exist
    LOCKED_FIELDS_WHILE_ACTIVE_VOTES = ('multiple_votes', 'can_vote_maybe', 'anyone_can_vote')
    
    url = forms.URLField(widget=forms.TextInput, required=False)

    class Meta:
        model = Poll
        fields = ('title', 'description', 'multiple_votes', 'can_vote_maybe', 'anyone_can_vote')
    
    def __init__(self, *args, **kwargs):
        super(_PollForm, self).__init__(*args, **kwargs)
        instance = kwargs.get('instance')
    
    def clean(self, *args, **kwargs):
        cleaned_data = super(_PollForm, self).clean(*args, **kwargs)
        return cleaned_data
        
    def save(self, *args, **kwargs):
        has_active_votes = self.instance.options.filter(votes__isnull=False).count() > 0
        if has_active_votes:
            print ">> TODO: reset initial values"
            import ipdb; ipdb.set_trace(); from pprint import pprint as pp;
        return super(_PollForm, self).save(*args, **kwargs)
        

PollForm = get_form(_PollForm)


class OptionForm(forms.ModelForm):

    class Meta:
        model = Option
        fields = ('description', 'image',)
        
    def clean(self, *args, **kwargs):
        """ Enforce selecting either an image or description or both. """
        data = super(OptionForm, self).clean(*args, **kwargs)
        description = self.cleaned_data.get('description', None)
        print ">> desc", description
        image = self.cleaned_data.get('image', None)
        print ">> imgage", image
        if not description and not image:
            raise forms.ValidationError(_('You must specify either an image or a description for this poll option!'))
        return data


class VoteForm(forms.Form):
    option = forms.IntegerField(required=True, widget=HiddenInput)
    choice = forms.ChoiceField(choices=Vote.VOTE_CHOICES, required=True)

    def get_label(self):
        pk = self.initial.get('option', None)
        if pk:
            return force_text(Option.objects.get(pk=pk))
        return ''
    
    
class PollNoFieldForm(forms.ModelForm):

    class Meta:
        model = Poll
        fields = ()
        
        
class CommentForm(forms.ModelForm):

    class Meta:
        model = Comment
        fields = ('text',)

