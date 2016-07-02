# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib import admin

from cosinnus_poll.models import Poll, Suggestion, Vote


class VoteInlineAdmin(admin.TabularInline):
    extra = 0
    list_display = ('from_date', 'to_date', 'poll')
    model = Vote


class SuggestionAdmin(admin.ModelAdmin):
    inlines = (VoteInlineAdmin,)
    list_display = ('from_date', 'to_date', 'poll', 'count')
    list_filter = ('poll__state', 'poll__creator', 'poll__group',)
    readonly_fields = ('poll', 'count')

    def get_readonly_fields(self, request, obj=None):
        if obj is None:
            # we create a new suggestion and the user should be able to select
            # an poll.
            return filter(lambda x: x != 'poll', self.readonly_fields)
        return super(SuggestionAdmin, self).get_readonly_fields(request, obj)


class SuggestionInlineAdmin(admin.TabularInline):
    extra = 0
    list_display = ('from_date', 'to_date', 'poll', 'count')
    model = Suggestion
    readonly_fields = ('count',)


class PollAdmin(admin.ModelAdmin):
    inlines = (SuggestionInlineAdmin,)
    list_display = ('title', 'from_date', 'to_date', 'creator', 'group',
                    'state')
    list_filter = ('state', 'creator', 'group',)
    search_fields = ('title', 'note')


admin.site.register(Poll, PollAdmin)
admin.site.register(Suggestion, SuggestionAdmin)
