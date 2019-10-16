# -*- coding: utf-8 -*-
# Implementation of the Tenant handlers
from globaleaks import models
from globaleaks.handlers.base import BaseHandler
from globaleaks.orm import transact
from globaleaks.state import State


def serialize_site(session, tenant, signup=None):
    ret = {
        'id': tenant.id,
        'label': tenant.label,
        'active': tenant.active,
        'subdomain': tenant.subdomain,
        'hostname': '',
        'onionservice': ''
    }

    if tenant.id in State.tenant_cache:
       tc = State.tenant_cache[tenant.id]

       if tc.mode == 'default':
           ret['hostname'] = tc.hostname
           ret['onionservice'] = tc.onionservice
       elif tenant.id in State.tenant_cache:
           rt = State.tenant_cache[1]
           ret['hostname'] = tenant.subdomain + '.' + rt.rootdomain
           ret['onionservice'] = tenant.subdomain + '.' + rt.onionservice

    return ret


@transact
def get_site_list(session):
    return [serialize_site(session, t) for t in session.query(models.Tenant).filter(models.Tenant.active == True)]


class SiteCollection(BaseHandler):
    check_roles = 'none'
    root_tenant_only = True

    def get(self):
        """
        Return the list of registered tenants
        """
        if 1 not in self.state.tenant_cache or not self.state.tenant_cache[1].multisite_login:
            return []

        return get_site_list()
