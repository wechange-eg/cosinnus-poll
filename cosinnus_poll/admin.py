# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib import admin

from cosinnus_poll.models import Poll, Option, Vote
from cosinnus.admin import BaseTaggableAdminMixin


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
            return [x for x in self.readonly_fields if x != 'poll']
        return super(OptionAdmin, self).get_readonly_fields(request, obj)


class OptionInlineAdmin(admin.TabularInline):
    extra = 0
    list_display = ('description', 'image', 'poll', 'count')
    model = Option
    readonly_fields = ('count',)


class PollAdmin(BaseTaggableAdminMixin, admin.ModelAdmin):
    inlines = BaseTaggableAdminMixin.inlines + [OptionInlineAdmin,]
    list_display = BaseTaggableAdminMixin.list_display + ['state',]
    list_filter = BaseTaggableAdminMixin.list_filter + ['state', ]
    search_fields = BaseTaggableAdminMixin.search_fields + ['']


admin.site.register(Poll, PollAdmin)
admin.site.register(Option, OptionAdmin)
