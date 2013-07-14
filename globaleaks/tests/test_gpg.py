import os
from twisted.internet.defer import inlineCallbacks
from twisted.trial import unittest

from globaleaks.tests import helpers
from globaleaks.rest import errors
from globaleaks.security import gpg_encrypt
from globaleaks.handlers import receiver
from globaleaks.settings import GLSetting
from globaleaks.tests.helpers import MockDict

from globaleaks.plugins.notification import MailNotification
from globaleaks.plugins.base import Event

GPGROOT = os.path.join(os.getcwd(), "testing_dir", "gnupg")

class TestReceiverSetKey(helpers.TestHandler):
    _handler = receiver.ReceiverInstance

    receiver_desc = {
        'username': 'vecna@useless_information_on_this_test.org',
        'name': 'assertion',
        'gpg_key_fingerprint': '341F1A8CE2B4F4F4174D7C21B842093DC6765430' }

    receiver_only_update = {
        'gpg_key_armor': None, 'gpg_key_remove': False,
        "gpg_key_info": None, "gpg_key_fingerprint": None,
        "gpg_key_status": None, # It's ignored what a Client send here
        "gpg_enable_notification": False,  "gpg_enable_files": False,

        'name' : "irrelevant",
        'password' : "",
        'old_password': "",
        'username' : "irrelevant",
        'notification_fields' : {'mail_address': 'am_i_ignored_or_not@email.xxx'},
        'description' : "A new description",
        "comment_notification": True,
        "file_notification": True,
        "tip_notification": False,
    }

    @inlineCallbacks
    def test_get(self):

        handler = self.request(self.dummyReceiver, role='receiver', user_id=self.dummyReceiver['receiver_gus'])
        yield handler.get()
        self.assertEqual(self.responses[0]['gpg_key_info'], None)

    @inlineCallbacks
    def test_update_key(self):

        self.receiver_only_update['gpg_key_armor'] = unicode(DeveloperKey.__doc__)
        self.receiver_only_update['gpg_key_remove'] = False
        handler = self.request(self.receiver_only_update, role='receiver', user_id=self.dummyReceiver['receiver_gus'])
        yield handler.put()
        self.assertEqual(self.responses[0]['gpg_key_fingerprint'],
            u'341F1A8CE2B4F4F4174D7C21B842093DC6765430')

        self.receiver_only_update['gpg_key_armor'] = unicode(HermesGlobaleaksKey.__doc__)
        self.receiver_only_update['gpg_key_remove'] = False
        handler = self.request(self.receiver_only_update, role='receiver', user_id=self.dummyReceiver['receiver_gus'])
        yield handler.put()
        self.assertEqual(self.responses[1]['gpg_key_fingerprint'],
            u'12CB52E0D793A11CAF0360F8839B5DED0050B3C1')

        # and the key has been updated!

    def test_handler_put_malformed_gpg_key(self):

        receiver_bad_update = dict(self.receiver_only_update)
        receiver_bad_update['gpg_key_armor'] = str((HermesGlobaleaksKey.__doc__).replace('A', 'B'))
        handler = self.request(receiver_bad_update, role='receiver', user_id=self.dummyReceiver['receiver_gus'])
        d = handler.put()
        self.assertFailure(d, errors.GPGKeyInvalid)
        return d

    def test_gpg_encryption(self):

        mail_support = MailNotification()

        dummy_template = { "en" : "In %EventTime% you've got a crush for Taryn Southern, yay!!"
                            "more info on: https://www.youtube.com/watch?v=C7JZ4F3zJdY "
                            "and know that you're not alone!" }

        mock_event = Event(type=u'tip', trigger='Tip',
                    notification_settings = dummy_template,
                    trigger_info = {'creation_date': '2013-05-13T17:49:26.105485', 'id': 'useless' },
                    node_info = MockDict().dummyNode,
                    receiver_info = MockDict().dummyReceiver,
                    context_info = MockDict().dummyContext,
                    plugin = MailNotification()  )

        mail_content = mail_support.format_template(dummy_template['en'], mock_event)

        # setup the GPG key before
        GLSetting.gpgroot = GPGROOT

        fake_receiver_desc = {
            'gpg_key_armor': unicode(DeveloperKey.__doc__),
            'gpg_key_fingerprint': u"341F1A8CE2B4F4F4174D7C21B842093DC6765430",
            'username': u'fake@username.net',
        }

        encrypted_body = gpg_encrypt(mail_content, fake_receiver_desc)
        self.assertSubstring('-----BEGIN PGP MESSAGE-----', encrypted_body)


    @inlineCallbacks
    def test_expired_key_error(self):

        self.receiver_only_update['gpg_key_armor'] = unicode(ExpiredKey.__doc__)
        self.receiver_only_update['gpg_key_remove'] = False
        handler = self.request(self.receiver_only_update, role='receiver', user_id=self.dummyReceiver['receiver_gus'])
        yield handler.put()
        self.assertEqual(self.responses[0]['gpg_key_fingerprint'],
            u'C6DAF5B34D5960883C7A9552AACA3A01C2752D4B')

        # ok, now has been imported the key, but we can't perform encryption
        body = ''.join(unichr(x) for x in range(0x370, 0x3FF))
        fake_serialized_receiver = {
            'gpg_key_armor': unicode(ExpiredKey.__doc__),
            'gpg_key_fingerprint': self.responses[0]['gpg_key_fingerprint'],
            'username': 'fake@username.net',
        }
        self.assertRaises(errors.GPGKeyInvalid, gpg_encrypt, body, fake_serialized_receiver)


class HermesGlobaleaksKey:
    """
-----BEGIN PGP PUBLIC KEY BLOCK-----
Version: GnuPG v1.4.11 (GNU/Linux)

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
OawA2tHlxKsF+0YpVn8cBOREJaAgogw5E+AbfqG+WKwWG6WZr8kFHQ0CH2bjUWC2
PMVbYDGyMqCreN5DfmB+rR1an1YS0YqJo+OF1KBULq5KU/vZoD0xUIBBBCCZ20/d
48OT8tRK5S4q0Xo+8nh4tD5HbG9iYUxlYWtzIChodHRwczovL3d3dy5nbG9iYWxl
YWtzLm9yZy8pIDxpbmZvQGdsb2JhbGVha3Mub3JnPokCPgQTAQIAKAIbLwYLCQgH
AwIGFQgCCQoLBBYCAwECHgECF4AFAlGnHgcFCQRtBQwACgkQg5td7QBQs8FqFRAA
u7QZl3SqoKq6uQ5Huh+Z/05yJ/SZCzXpbLjcI+rbQvzwk7+p2ez7DjDquaL+TcI/
hDjsxOWgweQZ+rI9ngzlFwAKK6+FIxZT5nfH6IXRwaTkQWNL2VMEcm0vvQ4t0Nap
eg6gQ5O8gHEVo49BnGsaICqfiD8YSk1Iz8vP3xwxx+KyYIkem2sz6XEOtpXODlp9
fMu4TzM0ofIzqjdNK1kutniKVXzPgfll8tXgrnaG56qjL7CvQUnAIufMfFPPUWiW
BRHI6jDB7VYHfmbD021qLTA3mTl3YsZepnG7sDhEPmiVmI6x2x+S1ExegcsTfs0q
42A6mUhT8imkAxoInOG7MaWs3ER/oVeCw2U+2uhusQ06W/0+1pKum/W9SKhfXHMc
oSw6w3siudBK8afFdMDfB6GYbS/hbLiieklljRv1ij70y+rKqYPXjiSo2jO4gXhI
XaX1+PzP/k+rYIa59GI437RQn0GO4eJF65U7P8Bz7sLUaya/nngul6VY3dhmAGze
2gk+9axMWvBfDOGe6s0IDKQsxFrd69cA2bOOsVEhpvyiHW28ylx/Ni11VVqKTUsy
ncRoatiQO7PSk6Qdk/jSyN6P9Ly9fqMk/j4MqVkdQxr16h7q0K6dGJt5dWIVnBWK
os8FoIi4v49E5+LZSQzVsShTMAweAnRZ46sItPUhroaIRgQQEQIABgUCTyJg0wAK
CRC4Qgk9xnZUMIcLAJ9pSib2QPWB6wqCAONe0X3NGWbtWACgtJ+Ya8SJkYceR/2r
x17Tr/kyPyyIRgQQEQIABgUCTymJogAKCRAkgE95gKtvMUCyAJ4hkb5JZjh7THHT
YiVHWuQ8qVN4DgCgotiFyw4gG/jrsdolhRbM7gb5sUyIRgQQEQIABgUCTxtOOQAK
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
71FdYqP5qSLo6/Xs/iA0dPaGXyE9
=0Iga
-----END PGP PUBLIC KEY BLOCK-----
    """
    pass

class DeveloperKey:
    """
-----BEGIN PGP PUBLIC KEY BLOCK-----
Version: GnuPG v1.4.11 (GNU/Linux)

mQGiBEqTwO0RBACqVdgJXs/vKv76HIudqQc9y/xSLoCxGd8mAxqjXn9fONAIrzDY
j79s1UMFCS8iTEH9EQGyv0JfCKXUcD1HFmKfZO8YfiBSM17SS+inPuV5+ZeQxvNh
ppzgit4jx+0DVMgBWYf/CvT5mPAFzA1U7mZFid/y/ITvEDeq42beOOXYkwCg/bUT
iw4R+Z0Q6LX++xhcidAQvqcD/iDACormazMFabPg45Bf7/lIHor2wGkzx46FuXbu
nxYyUXJQ88mU7szbhHdYhD2a3J1R/fUXuLsgQophWFBCKkq4YC3GKksKlQGKPgdS
WMxjxel4iaQJ5IZ48M+W/Y0eT+DSvARZw+IUr3q89JhS7mcxISlbocLz9Z32AGIj
olcxBACNUw6cJ7p5nCYjw9f+KQyU0NNx2/hGg+SBLRWiV5SaIarGDJG/KHurvsOA
yzjLEupXQvtaEyh5IeRu3rGr4hAfbtsIXRw8E055VBkwzXRN1rpcvumzayMW+OT8
M5lbU8u/5+PNTfmjOJsLdp40WWBRQrCr1F/xu3lyjQg0P78gu7QwQ2xhdWRpbyBB
Z29zdGkgPGNsYXVkaW8uYWdvc3RpQGxvZ2lvc2hlcm1lcy5vcmc+iGgEExEIACgC
GwMFCQfDDL8GCwkIBwMCBhUIAgkKCwQWAgMBAh4BAheABQJQeqODAAoJELhCCT3G
dlQwFfoAoIHqBJwQXb4uggiGJyqhLBENcU1XAKDIKet7mFlE4r3gfaWCmjevm+TT
MrQ7dmVjbmEgKGEgUmFuZG9tIEdsb2JhTGVrcyBEZXZlbG9wZXIpIDx2ZWNuYUBn
bG9iYWxlYWtzLm9yZz6IaAQTEQgAKAUCUHWpWAIbAwUJB8MMvwYLCQgHAwIGFQgC
CQoLBBYCAwECHgECF4AACgkQuEIJPcZ2VDDJVQCfbrtSyDNA3PSco8ILcPOUDSXr
sYAAn0X93PosYlznhqA3iiqEjPJm7X10tBh2ZWNuYSA8dmVjbmFAczBmdHBqLm9y
Zz6IawQTEQgAKwIbAwUJB8MMvwYLCQgHAwIGFQgCCQoLBBYCAwECHgECF4AFAlB6
o4MCGQEACgkQuEIJPcZ2VDBwlQCgu6Izv6NgQDKceRl43WWImtnJy0UAoPJNU3PW
r8q9nN64lzqRLxA27YPmtBx2ZWNuYSA8dmVjbmFAZGVsaXJhbmRvbS5uZXQ+iGgE
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
=bDVx
-----END PGP PUBLIC KEY BLOCK-----
    """
    pass

class ExpiredKey:
    """
-----BEGIN PGP PUBLIC KEY BLOCK-----
Version: GnuPG v1.4.11 (GNU/Linux)

mQGiBDmAu40RBAD13RF3ugwdmi+NdD7OeIhxHZVEN7wdTdYvksiX8CTzY0mpMGNA
JcRg2llQGddQ+vtEy4W+LVsreL3STbjNXx4n9ttrCvCtKUukxIF9iN5shSvOJqVJ
VvzLlqYIjYADVtWLlyLEZp67bKIB2wPuCX+5YnqNer+T8u2hip66tnVbEwCgwt8P
yZ5K4xqyIY1fxOH2M5YKxmcEAKsJ3l1wv1Zr3xzAi5k3ysY8bkiSjgV/AQ3FVKwc
iqjXx60PPSuzSLk2h7pspSpr8v3z7yuMi0w/+a+BcNNPMpZxv3CDtY2fVWfPbIJ4
T8pm9kiIyxc20tgbSwjdGTDIDlygz+EMAE4OB6XlzGJJLO448G7K38f4L2y+QMHu
GRdqBADObnvxMZRMzFrTjwryulPHYsxWnnRrHKlVnkw4AI+rp7IzeT39+OJxEpjb
U1xMvd269CW4cvu4RFHbYFy58DDDmbq1ibeksgRJtrBc08+c6X0at1Q6HJRzbcpt
r3ZYmfF78pTMzrzqy8DrKCdpbieIStCL0T3ChkAJupVwSTlfFojlBCARAgClBQJG
3lfdnh0BSSd2ZSBnZW5lcmF0ZWQgYSBuZXcga2V5LCBzaWduZWQgd2l0aCB0aGlz
IG9sZCBvbmUuIHRoZSBuZXcga2V5IGZpbmdlcnByaW50IGlzIEI5QjYgQUU4QSBG
NEJDIDMyNjEsIHZlY25hIChhdCkgczBmdHBqLm9yZywgd2luc3RvbnNtaXRoLmlu
Zm8sIGRlbGlyYW5kb20ubmV0AAoJEKrKOgHCdS1Llr0AoLtAd4PqWAxTjy3atxpO
IvER3kFsAKCjQ9GWO9+q1mu0E1QouJ4NDTkCDrQYdmVjbmEgPHZlY25hQHMwZnRw
ai5vcmc+iFYEExECABYFAjmAu40ECwoEAwMVAwIDFgIBAheAAAoJEKrKOgHCdS1L
o5YAoKB1yJi4No2kGDcWPwh/G6xde6seAKCXTJ7YZzqs+EZ84gyIB3Owfe1LEYhG
BBARAgAGBQI9OdJGAAoJEOEoOEbl8o3GQwQAnAsh+uTGlNxLfmTDmQfisfuvDksD
AJ0T+1nEkjQcyAw13ruLzdK5JuiASohJBDARAgAJBQI+xVNBAh0AAAoJEOEoOEbl
8o3Ga7oAoIeMJlgFPBQH/ZygOA5V/Or2BSViAKCJC+PirDgdNqjIM8iNwPGxnhbu
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
=SJOc
-----END PGP PUBLIC KEY BLOCK-----
    """
    pass
