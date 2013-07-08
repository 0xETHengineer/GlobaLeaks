import re

from twisted.internet.defer import inlineCallbacks

from globaleaks.tests import helpers

from globaleaks.rest import requests
from globaleaks.rest.base import uuid_regexp
from globaleaks.handlers import tip, base, admin, submission, files
from globaleaks.jobs import delivery_sched, cleaning_sched
from globaleaks import models
from globaleaks.utils import is_expired
from globaleaks.settings import transact
from globaleaks.tests.test_tip import TTip
from globaleaks.tests import helpers

from io import BytesIO as StringIO

STATIC_PASSWORD = u'bungabunga ;('

class MockHandler(base.BaseHandler):

    def __init__(self):
        pass

class TTip(helpers.TestWithDB):

    # filled in setup
    context_desc = None
    receiver1_desc = receiver2_desc = None
    submission_desc = None

    # filled while the emulation tests
    receipt = None
    itip_id = wb_tip_id = rtip1_id = rtip2_id = None
    wb_data = receiver1_data = receiver2_data = None

    # https://www.youtube.com/watch?v=ja46oa2ZML8 couple of cups, and tests!:

    tipContext = TTip.tipContext
    tipReceiver1 = TTip.tipReceiver1
    tipReceiver2 = TTip.tipReceiver2
    tipSubmission = TTip.tipSubmission
    tipOptions = TTip.tipOptions
    commentCreation = TTip.commentCreation

    dummyFile1 = {}
    dummyFile1['body'] = StringIO()
    dummyFile1['body'].write(str('aaaaaa'))
    dummyFile1['body_len'] = len(dummyFile1['body'].read())
    dummyFile1['content_type'] = 'application/octect'
    dummyFile1['filename'] = 'filename1'
    dummyFile2 = {}
    dummyFile2['body'] = StringIO()
    dummyFile2['body'].write(str('aaaaa'))
    dummyFile2['body_len'] = len(dummyFile2['body'].read())
    dummyFile2['content_type'] = 'application/octect'
    dummyFile2['filename'] = 'filename2'



class TestCleaning(TTip):
    _handler = tip.TipInstance

    # Test model is a prerequisite for create e valid environment where Tip lives

    # The test environment has one context (escalation 1, tip TTL 2, max file download 1)
    #                          two receiver ("first" level 1, "second" level 2)
    # Test context would just contain two receiver, one level 1 and the other level 2

    # They are defined in TTip. This unitTest DO NOT TEST HANDLERS but transaction functions

    @transact
    def test_cleaning(self, store):
        self.assertEqual(store.find(models.InternalTip).count(), 0)
        self.assertEqual(store.find(models.ReceiverTip).count(), 0)
        self.assertEqual(store.find(models.WhistleblowerTip).count(), 0)
        self.assertEqual(store.find(models.InternalFile).count(), 0)
        self.assertEqual(store.find(models.ReceiverFile).count(), 0)
        self.assertEqual(store.find(models.Comment).count(), 0)

    @inlineCallbacks
    def emulate_file_upload(self, associated_submission_id):
        relationship1 = files.dump_file_fs(self.dummyFile1)

        self.registered_file1 = yield files.register_file_db(
            self.dummyFile1, relationship1, associated_submission_id,
        )

        relationship2 = files.dump_file_fs(self.dummyFile2)

        self.registered_file2 = yield files.register_file_db(
            self.dummyFile2, relationship2, associated_submission_id,
        )

    @inlineCallbacks
    def do_create_internalfiles(self):
        yield self.emulate_file_upload(self.submission_desc['submission_gus'],)
        keydiff = set(['size', 'content_type', 'name', 'creation_date', 'id']) - set(self.registered_file1.keys())
        self.assertFalse(keydiff)
        keydiff = set(['size', 'content_type', 'name', 'creation_date', 'id']) - set(self.registered_file2.keys())
        self.assertFalse(keydiff)


    @inlineCallbacks
    def do_setup_tip_environment(self):

        basehandler = MockHandler()

        basehandler.validate_jmessage(self.tipContext, requests.adminContextDesc)
        self.context_desc = yield admin.create_context(self.tipContext)

        self.tipReceiver1['contexts'] = self.tipReceiver2['contexts'] = [ self.context_desc['context_gus'] ]
        basehandler.validate_jmessage( self.tipReceiver1, requests.adminReceiverDesc )
        basehandler.validate_jmessage( self.tipReceiver2, requests.adminReceiverDesc )

        try:
            self.receiver1_desc = yield admin.create_receiver(self.tipReceiver1)
        except Exception, e:
            print e
            self.assertTrue(False)

        self.receiver2_desc = yield admin.create_receiver(self.tipReceiver2)

        self.assertEqual(self.receiver1_desc['contexts'], [ self.context_desc['context_gus']])
        self.assertEqual(self.receiver2_desc['contexts'], [ self.context_desc['context_gus']])

        self.tipSubmission['context_gus'] = self.context_desc['context_gus']
        basehandler.validate_jmessage( self.tipSubmission, requests.wbSubmissionDesc)

        self.submission_desc = yield submission.create_submission(self.tipSubmission, finalize=False)

        self.assertEqual(self.submission_desc['wb_fields'], self.tipSubmission['wb_fields'])
        self.assertEqual(self.submission_desc['mark'], models.InternalTip._marker[0])

    @inlineCallbacks
    def do_finalize_submission(self):
        self.submission_desc['finalize'] = True
        self.submission_desc['wb_fields'] = helpers.fill_random_fields(self.context_desc)
        self.submission_desc = yield submission.update_submission(
            self.submission_desc['submission_gus'],
            self.submission_desc,
            finalize=True)

        self.assertEqual(self.submission_desc['mark'], models.InternalTip._marker[1])
        
        submission.create_whistleblower_tip(self.submission_desc)

    # -------------------------------------------
    # Those the two class implements the sequence
    # -------------------------------------------

class UnfinishedSubmissionCleaning(TestCleaning):

    @inlineCallbacks
    def submission_not_expired(self):
        """
        Submission is intended the non-finalized Tip, with a shorter life than completed Tips, and
        not yet delivered to anyone. (marker 0)
        """
        sub_list = yield cleaning_sched.get_tiptime_by_marker(models.InternalTip._marker[0])

        self.assertEqual(len(sub_list), 1)

        self.assertFalse(
            is_expired(
                cleaning_sched.iso2dateobj(sub_list[0]['creation_date']),
                sub_list[0]['submission_life_seconds'])
        )

    @inlineCallbacks
    def force_submission_expire(self):
        sub_list = yield cleaning_sched.get_tiptime_by_marker(models.InternalTip._marker[0])
        self.assertEqual(len(sub_list), 1)

        sub_desc = sub_list[0]
        sub_desc['submission_life_seconds'] = 0

        self.assertTrue(
            is_expired(
                cleaning_sched.iso2dateobj(sub_desc['creation_date']),
                sub_desc['submission_life_seconds'])
        )

        # and then, delete the expired submission
        yield cleaning_sched.itip_cleaning(sub_desc['id'])

        new_list = yield cleaning_sched.get_tiptime_by_marker(models.InternalTip._marker[0])
        self.assertEqual(len(new_list), 0)

    @inlineCallbacks
    def test_submission_life_and_expire(self):
        yield self.do_setup_tip_environment()
        yield self.submission_not_expired()
        yield self.force_submission_expire()


class FinalizedTipCleaning(TestCleaning):
    @inlineCallbacks
    def tip_not_expired(self):
        """
        Tip is intended InternalTip notified and delivered (marker 2, 'first' layer of deliverance)
        and their life depends by context policies
        """
        tip_list = yield cleaning_sched.get_tiptime_by_marker(models.InternalTip._marker[2])

        self.assertEqual(len(tip_list), 1)

        self.assertFalse(
            is_expired(
                cleaning_sched.iso2dateobj(tip_list[0]['creation_date']),
                tip_list[0]['tip_life_seconds'])
        )

    @inlineCallbacks
    def force_tip_expire(self):
        tip_list = yield cleaning_sched.get_tiptime_by_marker(models.InternalTip._marker[2])
        self.assertEqual(len(tip_list), 1)

        tip_desc  = tip_list[0]
        tip_desc['tip_life_seconds'] = 0

        self.assertTrue(
            is_expired(
                cleaning_sched.iso2dateobj(tip_desc['creation_date']),
                tip_desc['tip_life_seconds']
            )
        )
        
        # and then, delete the expired submission
        yield cleaning_sched.itip_cleaning(tip_desc['id'])

        new_list = yield cleaning_sched.get_tiptime_by_marker(models.InternalTip._marker[0])
        self.assertEqual(len(new_list), 0)

    @inlineCallbacks
    def do_create_receivers_tip(self):
        receiver_tips = yield delivery_sched.tip_creation()

        self.rtip1_id = receiver_tips[0]
        self.rtip2_id = receiver_tips[1]

        self.assertEqual(len(receiver_tips), 2)
        self.assertTrue(re.match(uuid_regexp, receiver_tips[0]))
        self.assertTrue(re.match(uuid_regexp, receiver_tips[1]))

    @inlineCallbacks
    def test_tip_life_and_expire(self):
        yield self.do_setup_tip_environment()       
        yield self.do_finalize_submission()
        yield self.do_create_receivers_tip()
        yield self.tip_not_expired()
        yield self.force_tip_expire()
        yield self.test_cleaning()

    @inlineCallbacks
    def test_tip_life_and_expire_with_files(self):
        yield self.do_setup_tip_environment()       
        yield self.do_create_internalfiles()
        yield self.do_finalize_submission()
        filesdict = yield delivery_sched.file_preprocess()
        processdict = yield delivery_sched.file_process(filesdict)
        receiverfile_list = yield delivery_sched.receiver_file_align(filesdict, processdict)
        yield self.do_create_receivers_tip()
        yield self.tip_not_expired()
        yield self.force_tip_expire()
        yield self.test_cleaning()
