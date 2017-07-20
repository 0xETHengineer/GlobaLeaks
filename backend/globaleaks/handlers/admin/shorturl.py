# -*- coding: UTF-8
#
#   shorturl
#   *****
# Implementation of the URL shortener handlers
#
from globaleaks import models
from globaleaks.handlers.base import BaseHandler
from globaleaks.orm import transact
from globaleaks.rest import requests, errors


def serialize_shorturl(shorturl):
    return {
        'id': shorturl.id,
        'shorturl': shorturl.shorturl,
        'longurl': shorturl.longurl
    }


@transact
def get_shorturl_list(store):
    shorturls = store.find(models.ShortURL)
    return [serialize_shorturl(shorturl) for shorturl in shorturls]


@transact
def create_shorturl(store, request):
    shorturl = models.ShortURL(request)
    store.add(shorturl)
    return serialize_shorturl(shorturl)


@transact
def delete_shorturl(store, shorturl_id):
    shorturl = store.find(models.ShortURL, models.ShortURL.id == shorturl_id).one()
    if not shorturl:
        raise errors.ShortURLIdNotFound

    store.remove(shorturl)



class ShortURLCollection(BaseHandler):
    check_roles = 'admin'
    cache_resource = True
    invalidate_cache = True

    def get(self):
        """
        Return the list of registered short urls
        """
        return get_shorturl_list()

    def post(self):
        """
        Create a new shorturl
        """
        request = self.validate_message(self.request.content.read(), requests.AdminShortURLDesc)

        return create_shorturl(request)


class ShortURLInstance(BaseHandler):
    check_roles = 'admin'

    def delete(self, shorturl_id):
        """
        Delete the specified shorturl.
        """
        return delete_shorturl(shorturl_id)
