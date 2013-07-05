# -*- coding: UTF-8
#
#   security 
#   ********
#
# GlobaLeaks security functions

import scrypt
import binascii
import time
import os
import shutil

from Crypto.Hash import SHA512
from Crypto.Random import random
from gnupg import GPG

from globaleaks.rest import errors
from globaleaks.utils import log, acquire_bool
from globaleaks.settings import GLSetting
from globaleaks.models import Receiver

SALT_LENGTH = (128 / 8) # 128 bits of unique salt

# this value can be incremented, but instead of the backend enforcing, we
# need a GLClient password strength checker
MINIMUM_PASSWORD_LENGTH = 4


def get_salt(salt_input):
    """
    @param salt_input:
        A string

    is performed a SHA512 hash of the salt_input string, and are returned 128bits
    of uniq data, converted in
    """
    sha = SHA512.new()
    sha.update(salt_input)
    # hex require two byte each to describe 1 byte of entropy
    return sha.hexdigest()[:SALT_LENGTH * 2]


def hash_password(proposed_password, salt_input):
    """
    @param proposed_password: a password, not security enforced.
        is not accepted an empty string.

    @return:
        the scrypt hash in base64 of the password
    """
    proposed_password = proposed_password.encode('utf-8')
    salt = get_salt(salt_input)

    if not len(proposed_password):
        log.err("password string has been not really provided (0 len)")
        raise errors.InvalidInputFormat("password expected for receiver")

    hashed_passwd = scrypt.hash(proposed_password, salt)
    return binascii.b2a_hex(hashed_passwd)


def check_password(guessed_password, base64_stored, salt_input):
    guessed_password = guessed_password.encode('utf-8')
    salt = get_salt(salt_input)

    hashed_guessed = scrypt.hash(guessed_password, salt)

    return binascii.b2a_hex(hashed_guessed) == base64_stored


def change_password(base64_stored, old_password, new_password, salt_input):
    """
    @param old_password: The old password in string, expected to be the same.
        If you're workin in Administrative context, just use set_receiver_password
        and override the old one.

    @param base64_stored:
    @param salt:
        You're fine with these

    @param new_password:
        Not security enforced, if wanted, need to be client or handler checked

    @return:
        the scrypt hash in base64 of the new password
    """
    if not check_password(old_password, base64_stored, salt_input):
        log.err("old_password provided do match")
        raise errors.InvalidOldPassword

    return hash_password(new_password, salt_input)


def insert_random_delay():
    """
    Time path analysis tests countermeasure
    """
    centisec = random.randint(1, 100) / 100.0
    time.sleep(centisec)


# GPG has not a dedicated class, because one of the function is callend inside a transact, and
# I'm not quite confident on creating an object that operates on the filesystem knowing
# that would be run also on the Storm cycle.
#
# functions
# base_import_key


class GLBGPG:

    def __init__(self, receiver_desc):
        """
        every time is needed, a new keyring is created here.
        """
        try:
            temp_gpgroot = os.path.join(GLSetting.gpgroot, "%s" % random.randint(0, 0xFFFF) )
            os.makedirs(temp_gpgroot)
            self.gpgh = GPG(gnupghome=temp_gpgroot, options="--trust-model always")
        except Exception as excep:
            log.err("Unable to instance GPG object: %s" % str(excep))
            raise excep

        self.receiver_desc = receiver_desc
        log.debug("GPG for receiver %s")


    def validate_key(self, armored_key):
        """
        @param armored_key:
        @return: True or False, True only if a key is effectively importable and listed.
        """

        self.ke = self.gpgh.import_keys(armored_key)

        # Error reported in stderr may just be warning, this is because is not raise an exception here
        if self.ke.stderr:
            log.err("Receiver %s in uploaded GPG key has raise and alarm:\n< %s >" %
                    (self.receiver_desc['username'], (self.ke.stderr.replace("\n", "\n  "))[:-3]))

        if not (hasattr(self.ke, 'results') and len(self.ke.results) == 1 and self.ke.results[0].has_key('fingerprint')):
            log.err("User error: unable to import GPG key in the keyring")
            return False

        # else, the key has been loaded and we extract info about that:
        self.fingerprint = self.ke.results[0]['fingerprint']

        # looking if the key is effectively reachable
        all_keys = self.gpgh.list_keys()

        self.keyinfo = u""
        for key in all_keys:
            if key['fingerprint'] == self.fingerprint:

                self.keyinfo += "Key length %s" % key['length']
                for uid in key['uids']:
                    self.keyinfo += "\n\t%s" % uid


        if not len(self.keyinfo):
            log.err("Key apparently imported but unable to be extracted info")
            return False

        return True


    def encrypt_file(self, plainpath, output_path):
        """
        @param gpg_key_armor:
        @param plainpath:
        @return:
        """
        if not self.validate_key(self.receiver_desc['gpg_key_armor']):
            raise errors.GPGKeyInvalid

        encrypt_obj = self.gpgh.encrypt_file(plainpath, str(self.receiver_desc['gpg_key_fingerprint']))

        if not encrypt_obj.ok:
            # continue here if is not ok
            log.err("Falure in encrypting file %s %s (%s)" % ( plainpath,
                    self.receiver_desc['username'], self.receiver_desc['gpg_key_fingerprint']) )
            log.err(encrypt_obj.stderr)
            raise errors.GPGKeyInvalid

        log.debug("Encrypting for %s (%s) file %s (%d boh ?)" %
                  (self.receiver_desc['username'], self.receiver_desc['gpg_key_fingerprint'],
                  plainpath, len(str(encrypt_obj))) )

        encrypted_path = os.path.join(output_path, "gpg_encrypted-%d-%d" %
                                      (random.randint(0, 0xFFFF), random.randint(0, 0xFFFF)))

        with file(encrypted_path, "w+") as f:
            f.write(str(encrypt_obj))

        return encrypted_path


    def encrypt_message(self, plaintext):
        """
        @param plaindata:
            An arbitrary long text that would be encrypted

        @param receiver_desc:

            The output of
                globaleaks.handlers.admin.admin_serialize_receiver()
            dictionary. It contain the fingerprint of the Receiver PUBKEY

        @return:
            The unicode of the encrypted output (armored)

        """
        if not self.validate_key(self.receiver_desc['gpg_key_armor']):
            raise errors.GPGKeyInvalid

        # This second argument may be a list of fingerprint, not just one
        encrypt_obj = self.gpgh.encrypt(plaintext, str(self.receiver_desc['gpg_key_fingerprint']) )

        if not encrypt_obj.ok:
            # else, is not .ok
            log.err("Falure in encrypting %d bytes for %s (%s)" % (len(plaintext),
                    self.receiver_desc['username'], self.receiver_desc['gpg_key_fingerprint']) )
            log.err(encrypt_obj.stderr)
            raise errors.GPGKeyInvalid

        log.debug("Encrypting for %s (%s) %d byte of plain data (%d cipher output)" %
                  (self.receiver_desc['username'], self.receiver_desc['gpg_key_fingerprint'],
                   len(plaintext), len(str(encrypt_obj))) )

        return str(encrypt_obj)


    def destroy_environment(self):
        try:
            shutil.rmtree(self.gpgh.gnupghome)
        except Exception as excep:
            log.err("Unable to clean temporary GPG environment: %s: %s" % (self.gpgh.gnupghome, excep))




# This is called in a @transact, when receiver update prefs and
# when admin configure a new key (at the moment, Admin GUI do not
# permit to sets preferences, but still the same function is
# used.
def gpg_options_parse(receiver, request):
    """
    @param receiver: the Storm object
    @param request: the Dict receiver by the Internets
    @return: None

    This function is called in create_recever and update_receiver
    and is used to manage the GPG options forced by the administrator

    This is needed also because no one of these fields are
    *enforced* by unicode_keys or bool_keys in models.Receiver

    GPG management, here are check'd these actions:
    1) Proposed a new GPG key, is imported to check validity, and
       stored in Storm DB if not error raise
    2) Removal of the present key

    Further improvement: update the keys using keyserver
    """

    new_gpg_key = request.get('gpg_key_armor', None)
    remove_key = request.get('gpg_key_remove', False)

    encrypt_notification = acquire_bool(request.get('gpg_enable_notification', False))
    encrypt_file = acquire_bool(request.get('gpg_enable_files', False))

    # set a default status
    receiver.gpg_key_status = Receiver._gpg_types[0]

    if remove_key:
        log.debug("User %s request to remove GPG key (%s)" %
                  (receiver.username, receiver.gpg_key_fingerprint))

        # In all the cases below, the key is marked disabled as request
        receiver.gpg_key_status = Receiver._gpg_types[0] # Disabled
        receiver.gpg_key_info = receiver.gpg_key_armor = receiver.gpg_key_fingerprint = None
        receiver.gpg_enable_files = receiver.gpg_enable_notification = False

    if new_gpg_key:

        fake_receiver_dict = { 'username' : receiver.username }
        gnob = GLBGPG(fake_receiver_dict)
        if not gnob.validate_key(new_gpg_key):
            raise errors.GPGKeyInvalid

        log.debug("GPG Key import success: %s" % gnob.keyinfo)

        receiver.gpg_key_info = gnob.keyinfo
        receiver.gpg_key_fingerprint = gnob.fingerprint
        receiver.gpg_key_status = Receiver._gpg_types[1] # Enabled
        receiver.gpg_key_armor = new_gpg_key

        gnob.destroy_environment()

    if receiver.gpg_key_status == Receiver._gpg_types[1]:
        receiver.gpg_enable_files = encrypt_file
        receiver.gpg_enable_notification = encrypt_notification
        log.debug("Receiver %s sets GPG usage: notification %s, file %s" %
                (receiver.username,
                 "YES" if encrypt_notification else "NO",
                 "YES" if encrypt_file else "NO") )
