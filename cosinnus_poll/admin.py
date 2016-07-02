# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib import admin

from cosinnus_poll.models import Poll, Option, Vote


class VoteInlineAdmin(admin.TabularInline):
    extra = 0
    list_display = ('description', 'image', 'poll')
    model = Vote


class OptionAdmin(admin.ModelAdmin):
    inlines = (VoteInlineAdmin,)
    list_display = ('poll', 'count')
    list_filter = ('poll__state', 'poll__creator', 'poll__group',)
    readonly_fields = ('poll', 'count')

    def get_readonly_fields(self, request, obj=None):
        if obj is None:
            # we create a new option and the user should be able to select
            # an poll.
            return filter(lambda x: x != 'poll', self.readonly_fields)
        return super(OptionAdmin, self).get_readonly_fields(request, obj)


class OptionInlineAdmin(admin.TabularInline):
    extra = 0
    list_display = ('description', 'image', 'poll', 'count')
    model = Option
    readonly_fields = ('count',)


class PollAdmin(admin.ModelAdmin):
    inlines = (OptionInlineAdmin,)
    list_display = ('title', 'creator', 'group', 'state')
    list_filter = ('state', 'creator', 'group',)
    search_fields = ('title', 'description', 'user__first_name', 'user__last_name', 'user__email', 'group__name')


admin.site.register(Poll, PollAdmin)
admin.site.register(Option, OptionAdmin)
