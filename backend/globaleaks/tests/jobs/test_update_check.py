# -*- coding: utf-8 -*-

from twisted.internet.defer import inlineCallbacks, succeed

from globaleaks import models
from globaleaks.jobs.update_check import UpdateCheck
from globaleaks.models import config
from globaleaks.orm import tw
from globaleaks.state import State
from globaleaks.tests import helpers

packages = b"Package: globaleaks\n" \
           b"Version: 0.0.1\n" \
           b"Filename: buster/globaleaks_1.0.0_all.deb\n\n" \
           b"Package: globaleaks\n" \
           b"Version: 1.0.0\n" \
           b"Filename: buster/globaleaks_1.0.0_all.deb\n\n" \
           b"Package: globaleaks\n" \
           b"Version: 1.2.3\n" \
           b"Filename: buster/globaleaks_1.0.0_all.deb\n\n" \
           b"Package: globaleaks\n" \
           b"Version: 2.0.666\n" \
           b"Filename: buster/globaleaks_2.0.9_all.deb\n\n" \
           b"Package: globaleaks\n" \
           b"Version: 2.0.1337\n" \
           b"Filename: buster/globaleaks_2.0.100_all.deb\n\n" \
           b"Package: tor2web\n" \
           b"Version: 31337\n" \
           b"Filename: buster/tor2web_31337_all.deb\n\n"


class TestUpdateCheck(helpers.TestGLWithPopulatedDB):
    @inlineCallbacks
    def test_refresh_works(self):
        State.tenant_cache[1].anonymize_outgoing_connections = False

        yield tw(config.db_set_config_variable, 1, 'latest_version', '0.0.1')
        yield self.test_model_count(models.Mail, 2)

        def fetch_packages_file_mock(self):
            return succeed(packages)

        UpdateCheck.fetch_packages_file = fetch_packages_file_mock

        yield UpdateCheck().operation()

        latest_version = yield tw(config.db_get_config_variable, 1, 'latest_version')
        self.assertEqual(latest_version, '2.0.1337')
        yield self.test_model_count(models.Mail, 3)
