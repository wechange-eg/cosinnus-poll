# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from os.path import join
import datetime

from django.core.urlresolvers import reverse
from django.db import models
from django.db.models import Q
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver
from django.utils import dateformat
from django.utils.encoding import python_2_unicode_compatible
from django.utils.formats import date_format
from django.utils.functional import cached_property
from django.utils.timezone import localtime, now
from django.utils.translation import ugettext_lazy as _, pgettext_lazy

from osm_field.fields import OSMField, LatitudeField, LongitudeField

from cosinnus_poll.conf import settings
from cosinnus_poll.managers import PollManager
from cosinnus.models import BaseTaggableObjectModel
from cosinnus.utils.permissions import filter_tagged_object_queryset_for_user
from cosinnus.utils.urls import group_aware_reverse
from cosinnus_poll import cosinnus_notifications
from django.contrib.auth import get_user_model
from cosinnus.utils.files import _get_avatar_filename


def localize(value, format):
    if (not format) or ("FORMAT" in format):
        return date_format(localtime(value), format)
    else:
        return dateformat.format(localtime(value), format)

def get_poll_image_filename(instance, filename):
    return _get_avatar_filename(instance, filename, 'images', 'polls')

@python_2_unicode_compatible
class Poll(BaseTaggableObjectModel):

    SORT_FIELDS_ALIASES = [
        ('title', 'title'),
        ('from_date', 'from_date'),
        ('to_date', 'to_date'),
        ('city', 'city'),
        ('state', 'state'),
    ]

    STATE_SCHEDULED = 1
    STATE_VOTING_OPEN = 2
    STATE_CANCELED = 3

    STATE_CHOICES = (
        (STATE_SCHEDULED, _('Scheduled')),
        (STATE_VOTING_OPEN, _('Voting open')),
        (STATE_CANCELED, _('Canceled')),
    )

    from_date = models.DateTimeField(
        _('Start'), default=None, blank=True, null=True, editable=True)

    to_date = models.DateTimeField(
        _('End'), default=None, blank=True, null=True, editable=True)

    state = models.PositiveIntegerField(
        _('State'),
        choices=STATE_CHOICES,
        default=STATE_VOTING_OPEN,
    )
    __state = None # pre-save purpose

    note = models.TextField(_('Note'), blank=True, null=True)

    suggestion = models.ForeignKey(
        'Suggestion',
        verbose_name=_('Poll date'),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='selected_name',
    )

    location = OSMField(_('Location'), blank=True, null=True)
    location_lat = LatitudeField(_('Latitude'), blank=True, null=True)
    location_lon = LongitudeField(_('Longitude'), blank=True, null=True)

    street = models.CharField(_('Street'), blank=True, max_length=50, null=True)

    zipcode = models.PositiveIntegerField(_('ZIP code'), blank=True, null=True)

    city = models.CharField(_('City'), blank=True, max_length=50, null=True)

    public = models.BooleanField(_('Is public (on website)'), default=False)

    image = models.ImageField(
        _('Image'),
        upload_to=get_poll_image_filename,
        blank=True,
        null=True)

    url = models.URLField(_('URL'), blank=True, null=True)

    objects = PollManager()

    class Meta(BaseTaggableObjectModel.Meta):
        ordering = ['from_date', 'to_date']
        verbose_name = _('Poll')
        verbose_name_plural = _('Polls')
        
    def __init__(self, *args, **kwargs):
        super(Poll, self).__init__(*args, **kwargs)
        self.__state = self.state

    def __str__(self):
        if self.state == Poll.STATE_SCHEDULED:
            if self.single_day:
                readable = _('%(poll)s (%(date)s - %(end)s)') % {
                    'poll': self.title,
                    'date': localize(self.from_date, 'd. F Y h:i'),
                    'end': localize(self.to_date, 'h:i'),
                }
            else:
                readable = _('%(poll)s (%(from)s - %(to)s)') % {
                    'poll': self.title,
                    'from': localize(self.from_date, 'd. F Y h:i'),
                    'to': localize(self.to_date, 'd. F Y h:i'),
                }
        else:
            readable = _('%(poll)s (pending)') % {'poll': self.title}
        return readable
    
    def save(self, *args, **kwargs):
        created = bool(self.pk) == False
        super(Poll, self).save(*args, **kwargs)

        if created:
            # poll/doodle was created
            if self.state == Poll.STATE_SCHEDULED:
                cosinnus_notifications.poll_created.send(sender=self, user=self.creator, obj=self, audience=get_user_model().objects.filter(id__in=self.group.members).exclude(id=self.creator.pk))
            else:
                cosinnus_notifications.doodle_created.send(sender=self, user=self.creator, obj=self, audience=get_user_model().objects.filter(id__in=self.group.members).exclude(id=self.creator.pk))
        if not created and self.__state == Poll.STATE_VOTING_OPEN and self.state == Poll.STATE_SCHEDULED:
            # poll went from being a doodle to being a real poll, so fire poll created
            cosinnus_notifications.poll_created.send(sender=self, user=self.creator, obj=self, audience=get_user_model().objects.filter(id__in=self.group.members).exclude(id=self.creator.pk))
        
        self.__state = self.state

    def get_absolute_url(self):
        kwargs = {'group': self.group, 'slug': self.slug}
        if self.state == Poll.STATE_VOTING_OPEN:
            return group_aware_reverse('cosinnus:poll:doodle-vote', kwargs=kwargs)
        return group_aware_reverse('cosinnus:poll:poll-detail', kwargs=kwargs)

    def set_suggestion(self, sugg=None, update_fields=['from_date', 'to_date', 'state', 'suggestion']):
        if sugg is None:
            # No suggestion selected or remove selection
            self.from_date = None
            self.to_date = None
            self.state = Poll.STATE_VOTING_OPEN
            self.suggestion = None
        elif sugg.poll.pk == self.pk:
            # Make sure to not assign a suggestion belonging to another poll.
            self.from_date = sugg.from_date
            self.to_date = sugg.to_date
            self.state = Poll.STATE_SCHEDULED
            self.suggestion = sugg
        else:
            return
        self.save(update_fields=update_fields)

    @property
    def single_day(self):
        return localtime(self.from_date).date() == localtime(self.to_date).date()

    def get_period(self):
        if self.single_day:
            return localize(self.from_date, "d.m.Y")
        else:
            return "%s - %s" % (localize(self.from_date, "d.m."), localize(self.to_date, "d.m.Y"))
    
    @classmethod
    def get_current(self, group, user):
        """ Returns a queryset of the current upcoming polls """
        qs = Poll.objects.filter(group=group)
        if user:
            qs = filter_tagged_object_queryset_for_user(qs, user)
        return upcoming_poll_filter(qs)
    
    @property
    def is_same_day(self):
        return localtime(self.from_date).date() == localtime(self.to_date).date()
    
    @property
    def is_same_time(self):
        return self.from_date.time() == self.to_date.time()
    
    def get_voters_pks(self):
        """ Gets the pks of all Users that have voted for this poll.
            Returns an empty list if nobody has voted or the poll isn't a doodle. """
        return self.suggestions.all().values_list('votes__voter__id', flat=True).distinct()


@python_2_unicode_compatible
class Suggestion(models.Model):
    from_date = models.DateTimeField(
        _('Start'), default=None, blank=False, null=False)

    to_date = models.DateTimeField(
        _('End'), default=None, blank=False, null=False)

    poll = models.ForeignKey(
        Poll,
        verbose_name=_('Poll'),
        on_delete=models.CASCADE,
        related_name='suggestions',
    )

    count = models.PositiveIntegerField(
        pgettext_lazy('the subject', 'Votes'), default=0, editable=False)

    class Meta:
        ordering = ['poll', '-count']
        unique_together = ('poll', 'from_date', 'to_date')
        verbose_name = _('Suggestion')
        verbose_name_plural = _('Suggestions')

    def __str__(self):
        if self.single_day:
            if self.from_date == self.to_date:
                return '%(date)s' % {
                    'date': localize(self.from_date, 'd. F Y H:i'),
                }
            return '%(date)s - %(end)s' % {
                'date': localize(self.from_date, 'd. F Y H:i'),
                'end': localize(self.to_date, 'H:i'),
            }
        return '%(from)s - %(to)s' % {
            'from': localize(self.from_date, 'd. F Y H:i'),
            'to': localize(self.to_date, 'd. F Y H:i'),
        }

    def get_absolute_url(self):
        return self.poll.get_absolute_url()

    def update_vote_count(self, count=None):
        self.count = self.votes.count()
        self.save(update_fields=['count'])

    @property
    def single_day(self):
        return localtime(self.from_date).date() == localtime(self.to_date).date()
    
    @cached_property
    def sorted_votes(self):
        return self.votes.order_by('voter__first_name', 'voter__last_name')

@python_2_unicode_compatible
class Vote(models.Model):
    
    VOTE_YES = 2
    VOTE_MAYBE = 1
    VOTE_NO = 0
    
    VOTE_CHOICES = (
        (VOTE_YES, _('Yes')),
        (VOTE_MAYBE, _('Maybe')),
        (VOTE_NO, _('No')),     
    )
    
    suggestion = models.ForeignKey(
        Suggestion,
        verbose_name=_('Suggestion'),
        on_delete=models.CASCADE,
        related_name='votes',
    )

    voter = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_('Voter'),
        on_delete=models.CASCADE,
        related_name='votes',
    )
    
    choice = models.PositiveSmallIntegerField(_('Vote'), blank=False, null=False,
        default=VOTE_NO, choices=VOTE_CHOICES)
    

    class Meta:
        unique_together = ('suggestion', 'voter')
        verbose_name = pgettext_lazy('the subject', 'Vote')
        verbose_name_plural = pgettext_lazy('the subject', 'Votes')

    def __str__(self):
        return 'Vote for %(poll)s: %(from)s - %(to)s' % {
            'poll': self.suggestion.poll.title,
            'from': localize(self.suggestion.from_date, 'd. F Y h:i'),
            'to': localize(self.suggestion.to_date, 'd. F Y h:i'),
        }

    def get_absolute_url(self):
        return self.suggestion.poll.get_absolute_url()



@python_2_unicode_compatible
class Comment(models.Model):
    creator = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name=_('Creator'), on_delete=models.PROTECT, related_name='poll_comments')
    created_on = models.DateTimeField(_('Created'), default=now, editable=False)
    last_modified = models.DateTimeField(_('Last modified'), auto_now=True, editable=False)
    poll = models.ForeignKey(Poll, related_name='comments')
    text = models.TextField(_('Text'))

    class Meta:
        ordering = ['created_on']
        verbose_name = _('Comment')
        verbose_name_plural = _('Comments')

    def __str__(self):
        return 'Comment on “%(poll)s” by %(creator)s' % {
            'poll': self.poll.title,
            'creator': self.creator.get_full_name(),
        }

    def get_absolute_url(self):
        if self.pk:
            return '%s#comment-%d' % (self.poll.get_absolute_url(), self.pk)
        return self.poll.get_absolute_url()
    
    def save(self, *args, **kwargs):
        created = bool(self.pk) == False
        super(Comment, self).save(*args, **kwargs)
        if created:
            # comment was created, message poll creator
            if not self.poll.creator == self.creator:
                cosinnus_notifications.poll_comment_posted.send(sender=self, user=self.creator, obj=self, audience=[self.poll.creator])
            # message votees (except comment creator and poll creator) if voting is still open
            votees_except_creator = [pk for pk in self.poll.get_voters_pks() if not pk in [self.creator_id, self.poll.creator_id]]
            if votees_except_creator and self.poll.state == Poll.STATE_VOTING_OPEN:
                cosinnus_notifications.voted_poll_comment_posted.send(sender=self, user=self.creator, obj=self, audience=get_user_model().objects.filter(id__in=votees_except_creator))
            # message all taggees (except comment creator)
            if self.poll.media_tag and self.poll.media_tag.persons:
                tagged_users_without_self = self.poll.media_tag.persons.exclude(id=self.creator.id)
                if len(tagged_users_without_self) > 0:
                    cosinnus_notifications.tagged_poll_comment_posted.send(sender=self, user=self.creator, obj=self, audience=list(tagged_users_without_self))
    
    @property
    def group(self):
        """ Needed by the notifications system """
        return self.poll.group



@receiver(post_delete, sender=Vote)
def post_vote_delete(sender, **kwargs):
    try:
        kwargs['instance'].suggestion.update_vote_count()
    except Suggestion.DoesNotExist:
        pass


@receiver(post_save, sender=Vote)
def post_vote_save(sender, **kwargs):
    kwargs['instance'].suggestion.update_vote_count()

   
def upcoming_poll_filter(queryset):
    """ Filters a queryset of polls for polls that begin in the future, 
    or have an end date in the future. Will always show all polls that ended today as well. """
    _now = now()
    poll_horizon = datetime.datetime(_now.year, _now.month, _now.day)
    return queryset.exclude(to_date__lt=poll_horizon).exclude(Q(to_date__isnull=True) & Q(from_date__lt=poll_horizon))

def past_poll_filter(queryset):
    """ Filters a queryset of polls for polls that began before today, 
    or have an end date before today. """
    _now = now()
    poll_horizon = datetime.datetime(_now.year, _now.month, _now.day)
    return queryset.exclude(to_date__gte=poll_horizon).exclude(Q(to_date__isnull=True) & Q(from_date__gte=poll_horizon))


import django
if django.VERSION[:2] < (1, 7):
    from cosinnus_poll import cosinnus_app
    cosinnus_app.register()
