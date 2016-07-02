# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from collections import defaultdict

from django.contrib import messages
from django.http import HttpResponseRedirect
from django.utils.translation import ugettext_lazy as _
from django.views.generic.base import RedirectView
from django.views.generic.detail import DetailView, SingleObjectMixin
from django.views.generic.edit import DeleteView, UpdateView, CreateView
from django.views.generic.list import ListView
from django.utils.timezone import now

from extra_views import (CreateWithInlinesView, FormSetView, InlineFormSet,
    UpdateWithInlinesView)

from django_ical.views import ICalFeed

from cosinnus.views.export import CSVExportView
from cosinnus.views.mixins.group import (RequireReadMixin, RequireWriteMixin,
    GroupFormKwargsMixin, FilterGroupMixin)
from cosinnus.views.mixins.user import UserFormKwargsMixin

from cosinnus.views.attached_object import AttachableViewMixin

from cosinnus_poll.conf import settings
from cosinnus_poll.forms import PollForm, SuggestionForm, VoteForm,\
    PollNoFieldForm, CommentForm
from cosinnus_poll.models import Poll, Suggestion, Vote, upcoming_poll_filter,\
    past_poll_filter, Comment
from django.shortcuts import get_object_or_404
from cosinnus.views.mixins.filters import CosinnusFilterMixin
from cosinnus_poll.filters import PollFilter
from cosinnus.utils.urls import group_aware_reverse
from cosinnus.utils.permissions import filter_tagged_object_queryset_for_user
from cosinnus.core.decorators.views import require_read_access,\
    require_user_token_access
from django.contrib.sites.models import Site, get_current_site


class PollIndexView(RequireReadMixin, RedirectView):

    def get_redirect_url(self, **kwargs):
        return group_aware_reverse('cosinnus:poll:list', kwargs={'group': self.group})

index_view = PollIndexView.as_view()


class PollListView(RequireReadMixin, FilterGroupMixin, CosinnusFilterMixin, ListView):

    model = Poll
    filterset_class = PollFilter
    poll_view = 'upcoming'
    show_past_polls = getattr(settings, 'COSINNUS_EVENT_CALENDAR_ALSO_SHOWS_PAST_EVENTS', False)
    
    def get_queryset(self):
        """ In the calendar we only show scheduled polls """
        qs = super(PollListView, self).get_queryset()
        qs = qs.filter(state=Poll.STATE_SCHEDULED)
        if not self.show_past_polls:
            qs = upcoming_poll_filter(qs)
        self.queryset = qs
        return qs
    
    def get_context_data(self, **kwargs):
        context = super(PollListView, self).get_context_data(**kwargs)
        doodle_count = super(PollListView, self).get_queryset().filter(state=Poll.STATE_VOTING_OPEN).count()
        future_polls_count = self.queryset.count() if not self.show_past_polls else upcoming_poll_filter(self.queryset).count()
        
        context.update({
            'future_polls': self.queryset,
            'future_polls_count': future_polls_count,
            'doodle_count': doodle_count,
            'poll_view': self.poll_view,
        })
        return context

list_view = PollListView.as_view()


class PastPollListView(PollListView):

    template_name = 'cosinnus_poll/poll_list_detailed_past.html'
    poll_view = 'past'
    
    def get_queryset(self):
        """ In the calendar we only show scheduled polls """
        qs = super(PollListView, self).get_queryset()
        qs = qs.filter(state=Poll.STATE_SCHEDULED)
        qs = past_poll_filter(qs).reverse()
        self.queryset = qs
        return qs
    
    def get_context_data(self, **kwargs):
        context = super(PastPollListView, self).get_context_data(**kwargs)
        context['past_polls'] = context.pop('future_polls')
        return context
    
past_polls_list_view = PastPollListView.as_view()


class DoodleListView(PollListView):
    template_name = 'cosinnus_poll/doodle_list.html'

    def get_queryset(self):
        """In the doodle list we only show polls with open votings"""
        qs = super(PollListView, self).get_queryset() # not this views, but poll views parent!!!
        qs = qs.filter(state=Poll.STATE_VOTING_OPEN)
        return qs

doodle_list_view = DoodleListView.as_view()


class DetailedPollListView(PollListView):
    template_name = 'cosinnus_poll/poll_list_detailed.html'
    
detailed_list_view = DetailedPollListView.as_view()

class SuggestionInlineView(InlineFormSet):
    extra = 1
    form_class = SuggestionForm
    model = Suggestion


class EntryFormMixin(RequireWriteMixin, FilterGroupMixin, GroupFormKwargsMixin,
                     UserFormKwargsMixin):
    form_class = PollForm
    model = Poll
    message_success = _('Poll "%(title)s" was edited successfully.')
    message_error = _('Poll "%(title)s" could not be edited.')

    def dispatch(self, request, *args, **kwargs):
        self.form_view = kwargs.get('form_view', None)
        return super(EntryFormMixin, self).dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(EntryFormMixin, self).get_context_data(**kwargs)
        tags = Poll.objects.tags()
        context.update({
            'tags': tags,
            'form_view': self.form_view,
        })
        return context

    def get_success_url(self):
        kwargs = {'group': self.group}
        # no self.object if get_queryset from add/edit view returns empty
        if hasattr(self, 'object'):
            kwargs['slug'] = self.object.slug
            urlname = 'cosinnus:poll:poll-detail'
        else:
            urlname = 'cosinnus:poll:list'
        return group_aware_reverse(urlname, kwargs=kwargs)

    def forms_valid(self, form, inlines):
        ret = super(EntryFormMixin, self).forms_valid(form, inlines)
        messages.success(self.request,
            self.message_success % {'title': self.object.title})
        return ret

    def forms_invalid(self, form, inlines):
        ret = super(EntryFormMixin, self).forms_invalid(form, inlines)
        if self.object:
            messages.error(self.request,
                self.message_error % {'title': self.object.title})
        return ret


class DoodleFormMixin(EntryFormMixin):
    inlines = [SuggestionInlineView]
    template_name = "cosinnus_poll/doodle_form.html"
    message_success = _('Unscheduled poll "%(title)s" was edited successfully.')
    message_error = _('Unscheduled poll "%(title)s" could not be edited.')

    def get_success_url(self):
        kwargs = {'group': self.group}
        # no self.object if get_queryset from add/edit view returns empty
        if hasattr(self, 'object'):
            kwargs['slug'] = self.object.slug
            urlname = 'cosinnus:poll:doodle-vote'
        else:
            urlname = 'cosinnus:poll:doodle-list'
        return group_aware_reverse(urlname, kwargs=kwargs)



class EntryAddView(EntryFormMixin, AttachableViewMixin, CreateWithInlinesView):
    message_success = _('Poll "%(title)s" was added successfully.')
    message_error = _('Poll "%(title)s" could not be added.')
    
    def forms_valid(self, form, inlines):
        form.instance.creator = self.request.user
        
        # polls are created as scheduled.
        # doodle polls would be created as STATE_VOTING_OPEN.
        form.instance.state = Poll.STATE_SCHEDULED
        return super(EntryAddView, self).forms_valid(form, inlines)
    
entry_add_view = EntryAddView.as_view()


class DoodleAddView(DoodleFormMixin, AttachableViewMixin, CreateWithInlinesView):
    message_success = _('Unscheduled poll "%(title)s" was added successfully.')
    message_error = _('Unscheduled poll "%(title)s" could not be added.')

    def forms_valid(self, form, inlines):
        form.instance.creator = self.request.user
        form.instance.state = Poll.STATE_VOTING_OPEN  # be explicit

        ret = super(DoodleAddView, self).forms_valid(form, inlines)

        # Check for non or a single suggestion and set it and inform the user
        num_suggs = self.object.suggestions.count()
        if num_suggs == 0:
            messages.info(self.request,
                _('You should define at least one date suggestion.'))
        return ret

doodle_add_view = DoodleAddView.as_view()


class EntryEditView(EntryFormMixin, AttachableViewMixin, UpdateWithInlinesView):
    pass

entry_edit_view = EntryEditView.as_view()


class DoodleEditView(DoodleFormMixin, AttachableViewMixin, UpdateWithInlinesView):

    def get_context_data(self, *args, **kwargs):
        context = super(DoodleEditView, self).get_context_data(*args, **kwargs)
        context.update({
            'has_active_votes': self.object.suggestions.filter(votes__isnull=False).count() > 0,
        })
        return context
    
    def forms_valid(self, form, inlines):
        # Save the suggestions first so we can directly
        # access the amount of suggestions afterwards
        for formset in inlines:
            formset.save()

        suggestion = form.cleaned_data.get('suggestion')
        if not suggestion:
            num_suggs = form.instance.suggestions.count()
            if num_suggs == 0:
                suggestion = None
                messages.info(self.request,
                    _('You should define at least one date suggestion.'))
        # update_fields=None leads to saving the complete model, we
        # don't need to call obj.self here
        # INFO: set_suggestion saves the instance
        form.instance.set_suggestion(suggestion, update_fields=None)

        return super(DoodleEditView, self).forms_valid(form, inlines)

doodle_edit_view = DoodleEditView.as_view()



class EntryDeleteView(EntryFormMixin, DeleteView):
    message_success = _('Poll "%(title)s" was deleted successfully.')
    message_error = _('Poll "%(title)s" could not be deleted.')

    def get_success_url(self):
        return group_aware_reverse('cosinnus:poll:list', kwargs={'group': self.group})

entry_delete_view = EntryDeleteView.as_view()


class DoodleDeleteView(EntryFormMixin, DeleteView):
    message_success = _('Unscheduled poll "%(title)s" was deleted successfully.')
    message_error = _('Unscheduled poll "%(title)s" could not be deleted.')

    def get_success_url(self):
        return group_aware_reverse('cosinnus:poll:doodle-list', kwargs={'group': self.group})

doodle_delete_view = DoodleDeleteView.as_view()



class EntryDetailView(RequireReadMixin, FilterGroupMixin, DetailView):

    model = Poll

    def get_context_data(self, **kwargs):
        context = super(EntryDetailView, self).get_context_data(**kwargs)
        return context

entry_detail_view = EntryDetailView.as_view()


class DoodleVoteView(RequireReadMixin, FilterGroupMixin, SingleObjectMixin,
        FormSetView):

    message_success = _('Your votes were saved successfully.')
    message_error = _('Your votes could not be saved.')

    extra = 0
    form_class = VoteForm
    model = Poll
    template_name = 'cosinnus_poll/doodle_vote.html'
    
    def post(self, request, *args, **kwargs):
        if self.get_object().state != Poll.STATE_VOTING_OPEN:
            messages.error(request, _('This is poll is already scheduled. You cannot vote for it any more.'))
            return HttpResponseRedirect(request.path)
        return super(DoodleVoteView, self).post(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(DoodleVoteView, self).get_context_data(**kwargs)
        
        # we group formsets, votes and suggestions by days (as in a day there might be more than one suggestion)
        # the absolute order inside the two lists when traversing the suggestions (iterated over days), 
        # is guaranteed to be sorted by date and time ascending, as is the user-grouped list of votes
        formset_forms_grouped = []
        vote_counts_grouped = []
        suggestions_list_grouped = []
        votes_user_grouped = defaultdict(list) # these are grouped by user, and sorted by suggestion, not day!
        for day, suggestions in sorted(self.suggestions_grouped.items(), key=lambda item: item[1][0].from_date):
            formset_forms_grouped_l = []
            vote_counts_grouped_l = []
            suggestions_list_grouped_l = []
            
            for suggestion in suggestions:
                suggestions_list_grouped_l.append(suggestion)
                # group the vote formsets in the same order we grouped the suggestions
                for form in context['formset'].forms:
                    if suggestion.pk == form.initial.get('suggestion', -1):
                        formset_forms_grouped_l.append(form)
                # create a grouped total count for all the votes
                # use sorted_votes here, it's cached
                # format: [no_votes, maybe_votes, yes_notes, is_most_overall_votes]
                counts = [0, 0, 0, False]
                for vote in suggestion.sorted_votes:
                    counts[vote.choice] += 1
                    votes_user_grouped[vote.voter.username].append(vote)
                vote_counts_grouped_l.append(counts)
            
            formset_forms_grouped.append(formset_forms_grouped_l)
            vote_counts_grouped.append(vote_counts_grouped_l)
            suggestions_list_grouped.append(suggestions_list_grouped_l)
        
        # determine and set the winning vote count of suggestions (if there are votes)
        try:
            max_vote_count = max([max([vote[2] for vote in votes]) for votes in vote_counts_grouped])
            for votes in vote_counts_grouped:
                for vote in votes:
                    if vote[2] == max_vote_count:
                        vote[3] = True
        except ValueError:
            pass
        
        context.update({
            'object': self.object,
            'suggestions': self.suggestions,
            'suggestions_grouped': suggestions_list_grouped,
            'formset_forms_grouped': formset_forms_grouped,
            'vote_counts_grouped': vote_counts_grouped,
            'votes_user_grouped': dict(votes_user_grouped),
        })
        return context

    def get_initial(self):
        self.object = self.get_object()
        self.suggestions = self.object.suggestions.order_by('from_date',
                                                            'to_date').all()
        
        self.suggestions_grouped = defaultdict(list)
        for suggestion in self.suggestions:
            self.suggestions_grouped[suggestion.from_date.date().isoformat()].append(suggestion)
                                                                    
        self.max_num = self.suggestions.count()
        self.initial = []
        for suggestion in self.suggestions:
            vote = None
            if self.request.user.is_authenticated():
                try:
                    vote = suggestion.votes.filter(voter=self.request.user).get()
                except Vote.DoesNotExist:
                    pass
            self.initial.append({
                'suggestion': suggestion.pk,
                'choice': vote.choice if vote else Vote.VOTE_NO,
            })
        return self.initial

    def get_success_url(self):
        kwargs = {'group': self.group, 'slug': self.object.slug}
        return group_aware_reverse('cosinnus:poll:doodle-vote', kwargs=kwargs)

    def formset_valid(self, formset):
        for form in formset:
            cd = form.cleaned_data
            suggestion = int(cd.get('suggestion'))
            choice = int(cd.get('choice', 0))
            if suggestion:
                vote, _created = Vote.objects.get_or_create(suggestion_id=suggestion,
                                           voter=self.request.user)
                vote.choice = choice
                vote.save()
        
        ret = super(DoodleVoteView, self).formset_valid(formset)
        messages.success(self.request, self.message_success )
        return ret
    
    def formset_invalid(self, formset):
        ret = super(DoodleVoteView, self).formset_invalid(formset)
        if self.object:
            messages.error(self.request, self.message_error)
        return ret


doodle_vote_view = DoodleVoteView.as_view()


class DoodleCompleteView(RequireWriteMixin, FilterGroupMixin, UpdateView):
    """ Completes a doodle poll for a selected suggestion, setting the poll to Scheduled. """
    form_class = PollNoFieldForm
    form_view = 'assign'
    model = Poll
    
    def get_object(self, queryset=None):
        obj = super(DoodleCompleteView, self).get_object(queryset)
        return obj
    
    def get(self, request, *args, **kwargs):
        # we don't accept GETs on this, just POSTs
        messages.error(request, _('The complete request can only be sent via POST!'))
        return HttpResponseRedirect(self.get_object().get_absolute_url())
    
    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        poll = self.object
        
        if self.object.state != Poll.STATE_VOTING_OPEN:
            messages.error(request, _('This is poll is already scheduled. You cannot vote for it any more.'))
            return HttpResponseRedirect(self.object.get_absolute_url())
        if 'suggestion_id' not in kwargs:
            messages.error(request, _('Poll cannot be completed: No date was supplied.'))
            return HttpResponseRedirect(self.object.get_absolute_url())
        
        suggestion = get_object_or_404(Suggestion, pk=kwargs.get('suggestion_id'))
        
        poll.from_date = suggestion.from_date
        poll.to_date = suggestion.to_date
        poll.state = Poll.STATE_SCHEDULED
        poll.save()
        
        messages.success(request, _('The poll was created successfully at the specified date.'))
        return HttpResponseRedirect(self.object.get_absolute_url())
    
doodle_complete_view = DoodleCompleteView.as_view()


class PollFeed(ICalFeed):
    """
    A simple poll calender feed. Uses a permanent user token for authentication
    (the token is only used for views displaying the user's poll-feeds).
    """
    PROTO_PRODUCT_ID = '-//%s//Poll//Feed'
    
    product_id = None
    timezone = 'UTC'
    title = _('Polls')
    description = _('Upcoming polls in')
    
    @require_user_token_access(settings.COSINNUS_EVENT_TOKEN_EVENT_FEED)
    def __call__(self, request, *args, **kwargs):
        site = get_current_site(request)
        
        self.title = '%s - %s' %  (self.group.name, self.title)
        self.description = '%s %s' % (self.description, self.group.name)
        if not self.product_id:
            self.product_id = PollFeed.PROTO_PRODUCT_ID % site.domain
        
        return super(PollFeed, self).__call__(request, *args, **kwargs)
    
    def get_feed(self, obj, request):
        self.request = request
        return super(PollFeed, self).get_feed(obj, request)
    
    def items(self, request):
        qs = Poll.get_current(self.group, self.user)
        qs = qs.filter(state=Poll.STATE_SCHEDULED, from_date__isnull=False, to_date__isnull=False).order_by('-from_date')
        return qs
    
    def item_title(self, item):
        return item.title

    def item_description(self, item):
        description = item.note
        # add website URL to description if set on poll
        if item.url:
            description = description + '\n\n' + item.url if description else item.url 
        return description

    def item_start_datetime(self, item):
        # we're returning a DateTime here. if we wanted to mark a full-day poll, we would return a Date
        return item.from_date
    
    def item_end_datetime(self, item):
        # we're returning a DateTime here. if we wanted to mark a full-day poll, we would return a Date
        return item.to_date
    
    def item_link(self, item):
        return item.get_absolute_url()
    
    def item_geolocation(self, item):
        mt = item.media_tag
        if mt and mt.location_lat and mt.location_lon:
            return (mt.location_lat, mt.location_lon)
        return None
    

poll_ical_feed = PollFeed()


class PollExportView(CSVExportView):
    fields = [
        'from_date',
        'to_date',
        'creator',
        'state',
        'note',
        'location',
        'street',
        'zipcode',
        'city',
        'public',
        'image',
        'url',
    ]
    model = Poll
    file_prefix = 'cosinnus_poll'

export_view = PollExportView.as_view()



class CommentCreateView(RequireWriteMixin, FilterGroupMixin, CreateView):

    form_class = CommentForm
    group_field = 'poll__group'
    model = Comment
    template_name = 'cosinnus_poll/poll_detail.html'
    
    message_success = _('Your comment was added successfully.')

    def form_valid(self, form):
        form.instance.creator = self.request.user
        form.instance.poll = self.poll
        messages.success(self.request, self.message_success)
        return super(CommentCreateView, self).form_valid(form)

    def get_context_data(self, **kwargs):
        context = super(CommentCreateView, self).get_context_data(**kwargs)
        # always overwrite object here, because we actually display the poll as object, 
        # and not the comment in whose view we are in when form_invalid comes back
        context.update({
            'poll': self.poll,
            'object': self.poll, 
        })
        return context

    def get(self, request, *args, **kwargs):
        self.poll = get_object_or_404(Poll, group=self.group, slug=self.kwargs.get('poll_slug'))
        return super(CommentCreateView, self).get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        self.poll = get_object_or_404(Poll, group=self.group, slug=self.kwargs.get('poll_slug'))
        self.referer = request.META.get('HTTP_REFERER', self.poll.group.get_absolute_url())
        return super(CommentCreateView, self).post(request, *args, **kwargs)
    
    def get_success_url(self):
        # self.referer is set in post() method
        return self.referer

comment_create = CommentCreateView.as_view()


class CommentDeleteView(RequireWriteMixin, FilterGroupMixin, DeleteView):

    group_field = 'poll__group'
    model = Comment
    template_name_suffix = '_delete'
    
    message_success = _('Your comment was deleted successfully.')
    
    def get_context_data(self, **kwargs):
        context = super(CommentDeleteView, self).get_context_data(**kwargs)
        context.update({'poll': self.object.poll})
        return context
    
    def post(self, request, *args, **kwargs):
        self.comment = get_object_or_404(Comment, pk=self.kwargs.get('pk'))
        self.referer = request.META.get('HTTP_REFERER', self.comment.poll.group.get_absolute_url())
        return super(CommentDeleteView, self).post(request, *args, **kwargs)

    def get_success_url(self):
        # self.referer is set in post() method
        messages.success(self.request, self.message_success)
        return self.referer

comment_delete = CommentDeleteView.as_view()


class CommentDetailView(SingleObjectMixin, RedirectView):

    model = Comment

    def get(self, request, *args, **kwargs):
        obj = self.get_object()
        return HttpResponseRedirect(obj.get_absolute_url())

comment_detail = CommentDetailView.as_view()


class CommentUpdateView(RequireWriteMixin, FilterGroupMixin, UpdateView):

    form_class = CommentForm
    group_field = 'poll__group'
    model = Comment
    template_name_suffix = '_update'

    def get_context_data(self, **kwargs):
        context = super(CommentUpdateView, self).get_context_data(**kwargs)
        context.update({'poll': self.object.poll})
        return context
    
    def post(self, request, *args, **kwargs):
        self.comment = get_object_or_404(Comment, pk=self.kwargs.get('pk'))
        self.referer = request.META.get('HTTP_REFERER', self.comment.poll.group.get_absolute_url())
        return super(CommentUpdateView, self).post(request, *args, **kwargs)

    def get_success_url(self):
        # self.referer is set in post() method
        return self.referer

comment_update = CommentUpdateView.as_view()

