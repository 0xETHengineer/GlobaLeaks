# -*- coding: UTF-8
#
#   gpgexpire_sched
#   ***************
#
# Implements a periodic checks to verify if keys configured by receiver are going
# to expire in short time, if so, send a warning email to the recipient.
# It's execute once per day.
import datetime

from twisted.internet.defer import inlineCallbacks

from globaleaks.jobs.base import GLJob
from globaleaks.models import Receiver
from globaleaks.settings import transact, GLSetting
from globaleaks.utils import sendmail, log
from globaleaks.security import get_expirations

__all__ = ['GPGExpireCheck']

untranslated_template ="""
This is an untranslated message from a GlobaLeaks node.
The PGP/GPG key configured by you: %s

Please extend their validity and update online, or upload a new
key.

When the key expire, if you've sets encrypted notification, they 
would not be send anymore at all.
"""


@transact
def check_expiration_date(store):

    all_rcvs = store.find(Receiver)

    keylist = []
    keytrack = {}

    for sr in all_rcvs:
        if sr.gpg_key_status == Receiver._gpg_types[1]: # Enabled
            keylist.append(sr.gpg_key_armor)

            if keytrack.has_key(sr.gpg_key_fingerprint):
                print "umh, duplicated key fingerprint between %s and %s" %\
                      (sr.user.username, keytrack[sr.gpg_key_fingerprint])

            keytrack.update({sr.gpg_key_fingerprint : sr.user.username })

    if not keytrack:
        log.debug("PGP/GPG key expiration check: no keys configured in this node")
        return (dict({}), dict({}), dict({}) )

    dates = get_expirations(keylist)

    today_dt = datetime.date.today()
    lowurgency = datetime.timedelta(weeks=2)
    highurgency = datetime.timedelta(days=3)

    # the return values
    expiring_keys_3d = {}
    expiring_keys_2w = {}
    expired_keys = {}

    for keyid, sincepoch in dates.iteritems():

        expiration_dt = datetime.datetime.utcfromtimestamp(int(sincepoch)).date()

        # simply, all the keys here are expired
        if expiration_dt < today_dt:
            continue

        key_timetolife = (expiration_dt - today_dt)

        if key_timetolife < highurgency:

            expiring_keys_3d.update({ keytrack[keyid]: sincepoch})
        elif key_timetolife < lowurgency:
            expiring_keys_2w.update({ keytrack[keyid]: sincepoch})
        else:
            expired_keys.update({ keytrack[keyid]: sincepoch })

    return (expiring_keys_2w, expiring_keys_3d, expired_keys)


class GPGExpireCheck(GLJob):

    @inlineCallbacks
    def operation(self):

        try:
            (two_weeks, three_days, gone) = yield check_expiration_date()

            messages = dict({})

            for username, sincepoch in two_weeks.iteritems():
                messages.update({ username : untranslated_template % "expire in two weeks" })

            for username, sincepoch in three_days.iteritems():
                messages.update({ username : untranslated_template % "expire in three days" })

            for username, sincepoch in gone.iteritems():
                messages.update({ username : untranslated_template % "it's already expired" })

            for recipient, message in messages.iteritems():

                mail_building = []

                mail_building.append("From: %s" % GLSetting.memory_copy.notif_source_email)
                    # GLSetting.memory_copy.notif_source_name,
                    # GLSetting.memory_copy.notif_source_email ) )
                mail_building.append("To: %s" % recipient)
                mail_building.append("Subject: GPG expiration date is incoming")
                mail_building.append("Content-Type: text/plain; charset=ISO-8859-1")
                mail_building.append("Content-Transfer-Encoding: 8bit\n")
                mail_building.append(message)

                sendmail(GLSetting.memory_copy.notif_username,
                         GLSetting.memory_copy.notif_password,
                         GLSetting.memory_copy.notif_username,
                         recipient,
                         "\n".join(mail_building),
                         GLSetting.memory_copy.notif_server,
                         GLSetting.memory_copy.notif_port,
                         GLSetting.memory_copy.notif_security)


        except Exception as excep:
            print "Error in key scheduler whatever"

