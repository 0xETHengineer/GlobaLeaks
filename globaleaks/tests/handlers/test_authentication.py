from globaleaks.tests import helpers
from globaleaks.handlers import authentication, admin, base
from globaleaks.rest import errors
from globaleaks.settings import GLSetting
from globaleaks import utils

from cyclone.util import ObjectDict

from twisted.internet.defer import inlineCallbacks

class ClassToTestUnauthenticatedDecorator(base.BaseHandler):
    @authentication.unauthenticated
    def get(self, *uriargs):
        self.set_status(200)
        self.finish("test")

class ClassToTestAuthenticatedDecorator(base.BaseHandler):
    @authentication.authenticated('admin')
    def get(self, *uriargs):
        self.set_status(200)
        self.finish("test")

class TestSessionUpdateOnUnauthRequests(helpers.TestHandler):
    _handler = ClassToTestUnauthenticatedDecorator

    @inlineCallbacks
    def test_successful_session_update_on_unauth_request(self):
        date1 = utils.datetime_now()
        
        GLSetting.sessions = {}
        GLSetting.sessions[u'antani'] = ObjectDict()
        GLSetting.sessions[u'antani']['user_id'] = u'admin'
        GLSetting.sessions[u'antani']['role'] = u'admin'
        GLSetting.sessions[u'antani']['id'] = u'antani'
        GLSetting.sessions[u'antani']['refreshdate'] = date1

        handler = self.request({}, headers={'X-Session': 'antani'})
        yield handler.get()
        
        date2 = GLSetting.sessions.values()[0].refreshdate
        
        self.assertNotEqual(date1, date2)

class TestSessionUpdateOnAuthRequests(helpers.TestHandler):
    _handler = ClassToTestAuthenticatedDecorator

    @inlineCallbacks
    def test_successful_session_update_on_auth_request(self):
        
        date1 = utils.datetime_now()
        
        GLSetting.sessions = {}
        GLSetting.sessions[u'antani'] = ObjectDict()
        GLSetting.sessions[u'antani']['user_id'] = u'admin'
        GLSetting.sessions[u'antani']['role'] = u'admin'
        GLSetting.sessions[u'antani']['id'] = u'antani'
        GLSetting.sessions[u'antani']['refreshdate'] = date1

        handler = self.request({}, headers={'X-Session': 'antani'})
        yield handler.get()
        
        date2 = GLSetting.sessions.values()[0].refreshdate
        
        self.assertNotEqual(date1, date2)

class TestSessionExpiryOnUnauthRequests(helpers.TestHandler):
    _handler = ClassToTestUnauthenticatedDecorator

    @inlineCallbacks
    def test_successful_session_expiry_on_unauth_request(self):
        
        date1 = utils.datetime_null() # oh a very old date!
        
        GLSetting.sessions = {}
        GLSetting.sessions[u'antani'] = ObjectDict()
        GLSetting.sessions[u'antani']['user_id'] = u'admin'
        GLSetting.sessions[u'antani']['role'] = u'admin'
        GLSetting.sessions[u'antani']['id'] = u'antani'
        GLSetting.sessions[u'antani']['refreshdate'] = date1

        handler = self.request({}, headers={'X-Session': 'antani'})
        
        # this request raise an exception for session expiration
        try:
            yield handler.get()
        except:
            pass
        
        self.assertTrue(handler.current_user is None)
        self.assertEqual(len(GLSetting.sessions.keys()), 0)

class TestSessionExpiryOnAuthRequests(helpers.TestHandler):
    _handler = ClassToTestAuthenticatedDecorator

    @inlineCallbacks
    def test_successful_session_expiry_on_auth_request(self):
        
        date1 = utils.datetime_null() # oh a very old date!
        
        GLSetting.sessions = {}
        GLSetting.sessions[u'antani'] = ObjectDict()
        GLSetting.sessions[u'antani']['user_id'] = u'admin'
        GLSetting.sessions[u'antani']['role'] = u'admin'
        GLSetting.sessions[u'antani']['id'] = u'antani'
        GLSetting.sessions[u'antani']['refreshdate'] = date1

        handler = self.request({}, headers={'X-Session': 'antani'})
        
        # this request raise an exception for session expiration
        try:
            yield handler.get()
        except:
            pass
        
        self.assertTrue(handler.current_user is None)
        self.assertEqual(len(GLSetting.sessions.keys()), 0)

class TestAuthentication(helpers.TestHandler):
    _handler = authentication.AuthenticationHandler

    @inlineCallbacks
    def test_successful_admin_login(self):
        handler = self.request({
           'username': 'admin',
           'password': 'globaleaks',
           'role': 'admin'
        })
        success = yield handler.post()
        self.assertTrue('session_id' in self.responses[0])
        self.assertEqual(len(GLSetting.sessions.keys()), 1)

    @inlineCallbacks
    def test_accept_admin_login_in_tor2web(self):
        handler = self.request({
            'username': 'admin',
            'password': 'globaleaks',
            'role': 'admin'
        }, headers={'X-Tor2Web': 'whatever'})
        GLSetting.memory_copy.tor2web_admin = True
        success = yield handler.post()
        self.assertTrue('session_id' in self.responses[0])
        self.assertEqual(len(GLSetting.sessions.keys()), 1)

    @inlineCallbacks
    def test_successful_receiver_login(self):
        handler = self.request({
           'username': self.dummyReceiverUser['username'],
           'password': helpers.VALID_PASSWORD1,
           'role': 'receiver'
        })
        success = yield handler.post()
        self.assertTrue('session_id' in self.responses[0])
        self.assertEqual(len(GLSetting.sessions.keys()), 1)

    @inlineCallbacks
    def test_successful_whistleblower_login(self):
        handler = self.request({
           'username': '',
           'password': self.dummyWBTip,
           'role': 'wb'
        })
        success = yield handler.post()
        self.assertTrue('session_id' in self.responses[0])
        self.assertEqual(len(GLSetting.sessions.keys()), 1)

    @inlineCallbacks
    def test_successful_admin_logout(self):
        # Login
        handler = self.request({
            'username': 'admin',
            'password': 'globaleaks',
            'role': 'admin'
        })
        success = yield handler.post()
        self.assertTrue(handler.current_user is None)
        self.assertTrue('session_id' in self.responses[0])
        self.assertEqual(len(GLSetting.sessions.keys()), 1)

        # Logout
        session_id = self.responses[0]['session_id']
        handler = self.request({}, headers={'X-Session': session_id})
        success = yield handler.delete()
        self.assertTrue(handler.current_user is None)
        self.assertEqual(len(GLSetting.sessions.keys()), 0)

        # A second logout must not be accepted (this validate also X-Session reuse)
        handler = self.request({}, headers={'X-Session': session_id})
        success = yield handler.delete()
        self.assertTrue(handler.current_user is None)
        self.assertEqual(len(GLSetting.sessions.keys()), 0)

    @inlineCallbacks
    def test_successful_receiver_logout(self):
        # Login
        handler = self.request({
            'username': self.dummyReceiver['username'],
            'password': helpers.VALID_PASSWORD1,
            'role': 'receiver'
        })
        success = yield handler.post()
        self.assertTrue(handler.current_user is None)
        self.assertTrue('session_id' in self.responses[0])
        self.assertEqual(len(GLSetting.sessions.keys()), 1)

        # Logout
        session_id = self.responses[0]['session_id']
        handler = self.request({}, headers={'X-Session': session_id})
        success = yield handler.delete()
        self.assertTrue(handler.current_user is None)
        self.assertEqual(len(GLSetting.sessions.keys()), 0)

        # A second logout must not be accepted (this validate also X-Session reuse)
        handler = self.request({}, headers={'X-Session': session_id})
        success = yield handler.delete()
        self.assertTrue(handler.current_user is None)
        self.assertEqual(len(GLSetting.sessions.keys()), 0)


    @inlineCallbacks
    def test_successful_whistleblower_logout(self):
        # Login
        handler = self.request({
            'username': '',
            'password': self.dummyWBTip,
            'role': 'wb'
        })
        success = yield handler.post()
        self.assertTrue(handler.current_user is None)
        self.assertTrue('session_id' in self.responses[0])
        self.assertEqual(len(GLSetting.sessions.keys()), 1)

        # Logout
        session_id = self.responses[0]['session_id']
        handler = self.request({}, headers={'X-Session': session_id})
        success = yield handler.delete()
        self.assertTrue(handler.current_user is None)
        self.assertEqual(len(GLSetting.sessions.keys()), 0)

        # A second logout must not be accepted (this validate also X-Session reuse)
        handler = self.request({}, headers={'X-Session': session_id})
        success = yield handler.delete()
        self.assertTrue(handler.current_user is None)
        self.assertEqual(len(GLSetting.sessions.keys()), 0)

    def test_invalid_admin_login_wrong_password(self):
        handler = self.request({
           'username': 'admin',
           'password': 'INVALIDPASSWORD',
           'role': 'admin'
        })
        d = handler.post()
        self.assertFailure(d, errors.InvalidAuthRequest)
        return d

    def test_invalid_receiver_login_wrong_password(self):
        handler = self.request({
           'username': 'receiver',
           'password': 'INVALIDPASSWORD',
           'role': 'receiver'
        })
        d = handler.post()
        self.assertFailure(d, errors.InvalidAuthRequest)
        return d

    def test_invalid_whistleblower_login_wrong_receipt(self):
        handler = self.request({
           'username': '',
           'password': 'INVALIDPASSWORD',
           'role': 'wb'
        })
        d = handler.post()
        self.assertFailure(d, errors.InvalidAuthRequest)
        return d

    def test_invalid_input_format_missing_role(self):
        handler = self.request({
           'username': '',
           'password': '',
        })
        d = handler.post()
        self.assertFailure(d, errors.InvalidInputFormat)
        return d

    def test_invalid_input_format_wrong_role(self):
        handler = self.request({
           'username': 'ratzinger',
           'password': '',
           'role': 'pope'
        })
        d = handler.post()
        self.assertFailure(d, errors.InvalidInputFormat)
        return d

    @inlineCallbacks
    def test_failed_login_counter(self):
        handler = self.request({
            'username': self.dummyReceiver['username'],
            'password': 'INVALIDPASSWORD',
            'role': 'receiver'
        })

        failed_login = 5
        for i in xrange(0, failed_login):
            try:
                failure = yield handler.post()
                print type(failure)
            except errors.InvalidAuthRequest:
                continue
            except Exception as excep:
                print excep, "Has been raised wrongly"
                self.assertTrue(False)

        receiver_status = yield admin.get_receiver(self.dummyReceiver['receiver_gus'])
        self.assertEqual(GLSetting.failed_login_attempts[self.dummyReceiver['username']], failed_login)

    @inlineCallbacks
    def test_bruteforce_login_protection(self):

        handler = self.request({
            'username': self.dummyReceiver['username'],
            'password': 'INVALIDPASSWORD',
            'role': 'receiver'
        })

        failed_login = 42
        for i in xrange(0, failed_login):
            try:
                failure = yield handler.post()
                print type(failure)
            except errors.InvalidAuthRequest:
                continue
            except Exception as excep:
                print excep, "Has been raised wrongly"
                self.assertTrue(False)

        receiver_status = yield admin.get_receiver(self.dummyReceiver['receiver_gus'])
        self.assertEqual(GLSetting.failed_login_attempts[self.dummyReceiver['username']], 42)

        # validate incremental delay
        for i in xrange(1, len(helpers.sleep_list)):
            self.assertTrue(i <= helpers.sleep_list[i])
            
