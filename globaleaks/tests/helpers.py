# -*- coding: UTF-8

import os
import json
import time
import uuid

from cyclone import httpserver
from cyclone.web import Application
from cyclone.util import ObjectDict as OD

from twisted.trial import unittest
from twisted.test import proto_helpers
from twisted.internet.defer import inlineCallbacks

from storm.twisted.testing import FakeThreadPool

from globaleaks.settings import GLSetting, transact
from globaleaks.handlers.admin import create_context, create_receiver, update_receiver
from globaleaks.handlers.submission import create_submission, create_whistleblower_tip
from globaleaks import db, utils, models, security
from globaleaks.third_party import rstr

from Crypto import Random
Random.atfork()

VALID_PASSWORD1 = u'justapasswordwithaletterandanumberandbiggerthan8chars'
VALID_PASSWORD2 = u'justap455w0rdwithaletterandanumberandbiggerthan8chars'
VALID_SALT1 = security.get_salt(rstr.xeger('[A-Za-z0-9]{56}'))
VALID_SALT2 = security.get_salt(rstr.xeger('[A-Za-z0-9]{56}'))
VALID_HASH1 = security.hash_password(VALID_PASSWORD1, VALID_SALT1)
VALID_HASH2 = security.hash_password(VALID_PASSWORD2, VALID_SALT2)

INVALID_PASSWORD = u'antani'

transact.tp = FakeThreadPool()

class TestWithDB(unittest.TestCase):
    def setUp(self):
        GLSetting.set_devel_mode()
        GLSetting.scheduler_threadpool = FakeThreadPool()
        GLSetting.sessions = {}
        GLSetting.working_path = os.path.abspath(os.path.join(GLSetting.root_path, 'testing_dir'))
        GLSetting.eval_paths()
        GLSetting.remove_directories()
        GLSetting.create_directories()
        return db.create_tables(create_node=True)

class TestGL(TestWithDB):

    @inlineCallbacks
    def _setUp(self):
        yield TestWithDB.setUp(self)
        self.setUp_dummy()
        yield self.fill_data()

    def setUp(self):
        return self._setUp()

    def setUp_dummy(self):

        dummyStuff = MockDict()

        self.dummyContext = dummyStuff.dummyContext
        self.dummySubmission = dummyStuff.dummySubmission
        self.dummyNotification = dummyStuff.dummyNotification
        self.dummyReceiverUser = dummyStuff.dummyReceiverUser
        self.dummyReceiver = dummyStuff.dummyReceiver
        self.dummyNode = dummyStuff.dummyNode

    @inlineCallbacks
    def fill_data(self):
        try:
            receiver = yield create_receiver(self.dummyReceiver)

            self.dummyReceiver['receiver_gus'] = receiver['receiver_gus']
        except Exception as excp:
            print "Fail fill_data/create_receiver: %s" % excp

        try:
            self.dummyContext['receivers'] = [ self.dummyReceiver['receiver_gus'] ]
            context = yield create_context(self.dummyContext)
            self.dummyContext['context_gus'] = context['context_gus']

        except Exception as excp:
            print "Fail fill_data/create_context: %s" % excp

        self.dummySubmission['context_gus'] = self.dummyContext['context_gus']
        self.dummySubmission['receivers'] = [ self.dummyReceiver['receiver_gus'] ]
        self.dummySubmission['wb_fields'] = fill_random_fields(self.dummyContext)

        try:
            submission = yield create_submission(self.dummySubmission, finalize=True)
            self.dummySubmission['id'] = submission['id']
            self.dummySubmission['submission_gus'] = submission['submission_gus']
        except Exception as excp:
            print "Fail fill_data/create_submission: %s" % excp

        try:
            self.dummyWBTip = yield create_whistleblower_tip(self.dummySubmission)
        except Exception as excp:
            print "Fail fill_data/create_whistleblower: %s" % excp


    def localization_set(self, dict_l, dict_c, language):
        ret = dict(dict_l)

        for attr in getattr(dict_c, "localized_strings"):
            ret[attr] = {}
            ret[attr][language] = unicode(dict_l[attr])
        
        return ret

class TestHandler(TestGL):
    """
    :attr _handler: handler class to be tested
    """
    _handler = None

    @inlineCallbacks
    def setUp(self):
        """
        override default handlers' get_store with a mock store used for testing/
        """
        yield TestGL.setUp(self)
        self.responses = []

        @classmethod
        def mock_write(cls, response=None):
            # !!!
            # Here we are making the assumption that every time write() get's
            # called it contains *all* of the response message.
            if response:
                self.responses.append(response)

        self._handler.write = mock_write
        # we make the assumption that we will always use call finish on write.
        self._handler.finish = mock_write

        # we need to reset settings.session to keep each test independent
        GLSetting.sessions = dict()


    def request(self, jbody=None, role=None, user_id=None, headers=None, body='',
            remote_ip='0.0.0.0', method='MOCK'):

        """
        Function userful for performing mock requests.

        Args:

            jbody:
                The body of the request as a dict (it will be automatically
                converted to string)

            body:
                The body of the request as a string

            role:
                If we should perform authentication role can be either "admin",
                "receiver" or "wb"

            user_id:
                If when performing authentication the session should be bound
                to a certain user_id.

            method:
                HTTP method, e.g. "GET" or "POST"

            uri:
                URL to fetch

            role:
                the role

            headers:
                (dict or :class:`cyclone.httputil.HTTPHeaders` instance) HTTP
                headers to pass on the request

            remote_ip:
                If a particular remote_ip should be set.

        """
        if jbody and not body:
            body = json.dumps(jbody)
        elif body and jbody:
            raise ValueError('jbody and body in conflict')

        application = Application([])

        tr = proto_helpers.StringTransport()
        connection = httpserver.HTTPConnection()
        connection.factory = application
        connection.makeConnection(tr)

        request = httpserver.HTTPRequest(uri='mock',
                                         method=method,
                                         headers=headers,
                                         body=body,
                                         remote_ip=remote_ip,
                                         connection=connection)

        handler = self._handler(application, request)

        @classmethod
        def mock_pass(cls, *args):
            pass
        # so that we don't complain about XSRF
        handler.check_xsrf_cookie = mock_pass

        if role:
            session_id = '4tehlulz'
            new_session = OD(
                   refreshdate=utils.datetime_now(),
                   id=session_id,
                   role=role,
                   user_id=user_id
            )
            GLSetting.sessions[session_id] = new_session
            handler.request.headers['X-Session'] = session_id
        return handler


class MockDict():
    """
    This class just create all the shit we need for emulate a GLNode
    """

    def __init__(self):

        self.dummyReceiverUser = {
            'username': u'maker@iz.cool.yeah',
            'password': VALID_HASH1,
            'salt': VALID_SALT1,
            'role': u'admin',
            'state': u'enabled',
            'last_login': utils.datetime_null(),
            'first_failed': utils.datetime_null(),
            'failed_login_count': 0
        }

        self.dummyReceiver = {
            'receiver_gus': unicode(uuid.uuid4()),
            'password': VALID_PASSWORD1,
            'name': u'Ned Stark',
            'description': u'King MockDummy Receiver',
            'notification_fields': {'mail_address': self.dummyReceiverUser['username']},
            'username': self.dummyReceiverUser['username'],
            'can_delete_submission': True,
            'receiver_level': 1,
            'contexts' : [],
            'tags': [ u'first', u'second', u'third' ],
            'tip_notification': True,
            'file_notification': True,
            'comment_notification': True,
            'gpg_key_info': u'',
            'gpg_key_fingerprint' : u'',
            'gpg_key_status': models.Receiver._gpg_types[0], # disabled
            'gpg_key_armor' : u'',
            'gpg_enable_notification': True,
            'gpg_enable_files': True,
            'gpg_key_remove': False
        }

        self.dummyContext = {
            'context_gus': unicode(uuid.uuid4()),
            # localized stuff
            'name': u'created by shooter',
            'receipt_description': u'xx',
            'submission_introduction': u'yy',
            'submission_disclaimer': u'kk',
            'description': u'This is the update',
            # fields, usually overwritten in content by fill_random_fields
            'fields': [
                  {"name": "Short title",
                   "hint": "Describe your tip-off with a line/title",
                   "required": True,
                   "presentation_order": 1,
                   "value": "",
                   "key": "Short title",
                   "type": "text"
                  },
                  {"name": "Full description",
                   "hint": "Describe the details of your tip-off",
                   "required": True,
                    "presentation_order": 2,
                    "value": "",
                    "key": "Full description",
                    "type": "text"
                  },
                  {"name": "Files description",
                   "hint": "Describe the submitted files",
                   "required": False,
                   "presentation_order": 3,
                   "value": "",
                   "key": "Files description",
                   "type": "text"}
                 ],
            'selectable_receiver': False,
            'tip_max_access': 10,
            # tip_timetolive is expressed in days
            'tip_timetolive': 20,
            # submission_timetolive is expressed in hours
            'submission_timetolive': 48,
            'file_max_download' :1,
            'escalation_threshold': 1,
            'receivers' : [],
            'tags': [],
            'receipt_regexp': u'[A-Z]{4}\+[0-9]{5}',
            'file_required': False,
            'select_all_receivers': True,
        }

        self.dummySubmission = {
            'context_gus': '',
            'wb_fields': fill_random_fields(self.dummyContext),
            'finalize': False,
            'receivers': [],
        }

        self.dummyNode = {
            'name':  u"Please, set me: name/title",
            'description':  u"Please, set me: description",
            'presentation': u'This is what appears on top',
            'hidden_service':  u"http://1234567890123456.onion",
            'public_site':  u"https://globaleaks.org",
            'email':  u"email@dumnmy.net",
            'stats_update_time':  2, # hours,
            'languages_supported':  [ ], # It's ignored, but expect a list
            'languages_enabled':  [ "it" , "en" ],
            'default_language': 'en',
            'password' : '',
            'old_password' : '',
            'salt': 'OMG!, the Rains of Castamere ;( ;(',
            'salt_receipt': '<<the Lannisters send their regards>>',
            'maximum_descsize' : GLSetting.defaults.maximum_descsize,
            'maximum_filesize' : GLSetting.defaults.maximum_filesize,
            'maximum_namesize' : GLSetting.defaults.maximum_namesize,
            'maximum_textsize' : GLSetting.defaults.maximum_textsize,
            'tor2web_admin' : True,
            'tor2web_submission' : True,
            'tor2web_tip' : True,
            'tor2web_receiver' : True,
            'tor2web_unauth' : True,
            'exception_email' : GLSetting.defaults.exception_email,
        }

        self.dummyNotification = {
            'server': u'mail.foobar.xxx',
            'port': 12345,
            'username': u'staceppa',
            'password': u'antani',
            'security': u'SSL',
            'source_name': u'UnitTest Helper Name',
            'source_email': u'unit@test.helper',
            'tip_template': u'tip message: %sNodeName%',
            'comment_template': u'comment message: %sNodeName%',
            'file_template': u'file message: %sNodeName%',
            'activation_template': u'activation message: %sNodeName%',
            'tip_mail_title': u'xxx',
            'comment_mail_title': u'yyy',
            'file_mail_title': u'kkk',
            'activation_mail_title': u'uuu',
        }


def fill_random_fields(context_desc):
    """
    getting the context dict, take 'fields'.
    then populate a valid dict of key : value, usable as wb_fields

    """
    assert context_desc
    fields_list = context_desc['fields']
    assert len(fields_list) >= 1

    ret_dict = {}
    for sf in fields_list:

        assert sf.has_key(u'name')
        assert sf.has_key(u'key')
        assert sf.has_key(u'hint')
        assert sf.has_key(u'presentation_order')
        assert sf.has_key(u'value')
        assert sf.has_key(u'type')
        # assert sf.has_key(u'required')

        unicode_weird = ''.join(unichr(x) for x in range(0x400, 0x4FF) )
        ret_dict.update({ sf.get(u'key') : unicode_weird })

    return ret_dict
