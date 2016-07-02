# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from haystack import indexes

from cosinnus.utils.search import BaseTaggableObjectIndex

from cosinnus_poll.models import Poll


class PollIndex(BaseTaggableObjectIndex, indexes.Indexable):
    description = indexes.CharField(model_attr='description', null=True)
    location = indexes.CharField(model_attr='location', null=True)
    street = indexes.CharField(model_attr='street', null=True)
    zipcode = indexes.CharField(model_attr='zipcode', null=True)
    city = indexes.CharField(model_attr='city', null=True)

    image = indexes.CharField(model_attr='image', indexed=False, null=True)
    url = indexes.CharField(model_attr='url', indexed=False, null=True)

    def get_model(self):
        return Poll

