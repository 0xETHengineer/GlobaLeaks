# -*- coding: UTF-8
#
#   overview
#   ********
# Implementation of the code executed when an HTTP client reach /overview/* URI

import os

from globaleaks.settings import transact, GLSetting
from globaleaks.handlers.base import BaseHandler
from globaleaks.handlers.authentication import authenticated, transport_security_check
from globaleaks import models

from twisted.internet.defer import inlineCallbacks
from globaleaks.utils import pretty_date_time, pretty_diff_now, log


@transact
def collect_tip_overview(store):

    tip_description_list = []
    all_itips = store.find(models.InternalTip)

    for itip in all_itips:
        tip_description = {
            "id": itip.id,
            "creation_date": pretty_date_time(itip.creation_date),
            "creation_lifetime": pretty_diff_now(itip.creation_date),
            "expiration_date": pretty_date_time(itip.expiration_date),
            "context_id": itip.context_id,
            "context_name": itip.context.name,
            "pertinence_counter": itip.pertinence_counter,
            "status": itip.mark,
            "receivertips": [],
            "internalfiles": [],
            "comments": [],
        }

        # strip uncompleted submission, until GLClient open new submission
        # also if no data has been supply
        if itip.mark == models.InternalTip._marker[0]:
            continue

        for rtip in itip.receivertips:
            tip_description['receivertips'].append({
                'access_counter': rtip.access_counter,
                'notification_date': pretty_date_time(rtip.notification_date),
                # 'creation_date': pretty_date_time(rtip.creation_date),
                'status': rtip.mark,
                'receiver_id': rtip.receiver.id,
                'receiver_username': rtip.receiver.username,
                'receiver_name': rtip.receiver.name,
                # last_access censored willingly
            })

        for ifile in itip.internalfiles:
            tip_description['internalfiles'].append({
                'name': ifile.name,
                'size': ifile.size,
                'status': ifile.mark,
                'content_type': ifile.content_type
            })

        for comment in itip.comments:
            tip_description['comments'].append({
                'type': comment.type,
                'lifetime': pretty_diff_now(comment.creation_date),
            })

        # whistleblower tip has not a reference from itip, then:
        wbtip = store.find(models.WhistleblowerTip,
            models.WhistleblowerTip.internaltip_id == itip.id).one()

        if wbtip is not None:
            tip_description.update({
                'wb_access_counter': wbtip.access_counter,
                'wb_last_access': pretty_diff_now(wbtip.last_access)
            })
        else:
            tip_description.update({
                'wb_access_counter': u'Deleted', 'wb_last_access': u'Never'
            })

        tip_description_list.append(tip_description)

    return tip_description_list


@transact
def collect_users_overview(store):

    users_description_list = []

    all_receivers = store.find(models.Receiver)

    for receiver in all_receivers:
        # all public of private infos are stripped, because know between the Admin resources
        user_description = {
            'id': receiver.id,
            'name': receiver.name,
            'failed_login': receiver.failed_login,
            'receiverfiles': [],
            'receivertips': [],
        }

        rcvr_files = store.find(models.ReceiverFile, models.ReceiverFile.receiver_id == receiver.id )
        for rfile in rcvr_files:
            user_description['receiverfiles'].append({
                'internatip_id': rfile.id,
                'file_name': rfile.internalfile.name,
                'downloads': rfile.downloads,
                'last_access': pretty_diff_now(rfile.last_access),
                'status': rfile.mark,
            })

        rcvr_tips = store.find(models.ReceiverTip, models.ReceiverTip.receiver_id == receiver.id )
        for rtip in rcvr_tips:
            user_description['receivertips'].append({
                'internaltip_id': rtip.id,
                'status': rtip.mark,
                'last_access': pretty_diff_now(rtip.last_access),
                'notification_date': pretty_diff_now(rtip.notification_date),
                'access_counter': rtip.access_counter,
            })

        users_description_list.append(user_description)

    return users_description_list

@transact
def collect_files_overview(store):

    file_description_list = []

    submission_dir = os.path.join(GLSetting.working_path, GLSetting.submission_path)
    disk_files = os.listdir(submission_dir)
    stored_ifiles = store.find(models.InternalFile)

    for ifile in stored_ifiles:

        file_desc = {
            'id': ifile.id,
            'name': ifile.name,
            'content_type': ifile.content_type,
            'size': ifile.size,
            'itip': ifile.internaltip_id,
            'creation_date': pretty_date_time(ifile.creation_date),
            'rfiles': 0,
            'stored': None,
            'path': '',
        }

        #file_desc['rfiles_associated'] = store.find(models.ReceiverFile,
        #                models.ReceiverFile.internalfile_id == ifile.id).count()
        if hasattr(ifile, 'receiverfiles'):
            log.debug("Comunque ha il receiverfiles, e il count est %d" % ifile.receiverfiles.count())

        absfilepath = os.path.join(submission_dir, ifile.file_path)

        if os.path.isfile(absfilepath):

            file_desc['stored'] = True
            file_desc['path'] = absfilepath

            # disk_files contain all the files present, the InternalFiles
            # are removed one by one, and the goal is to keep in disk_files
            # all the not referenced files.
            if ifile.file_path in disk_files:
                disk_files.remove(ifile.file_path)
            else:
                log.err("Weird failure: path %s not found in %s but still on dir" %
                    (ifile.file_path, submission_dir) )

        else:
            log.err("InternalFile %s has not a disk reference present")
            file_desc['stored'] = False

        file_description_list.append(file_desc)

    # the files remained in disk_files array are without ifile
    for dfile in disk_files:

        absfilepath = os.path.join(submission_dir, dfile)

        file_desc = {
            'id': '',
            'name': '',
            'content_type': '',
            'size': os.stat(absfilepath).st_size,
            'itip': '',
            'rfiles_associated': 0,
            'stored': True,
            'path': absfilepath,
        }

        file_description_list.append(file_desc)

    return file_description_list



class Tips(BaseHandler):
    """
    A9

    /admin/overview/tips
    """

    @inlineCallbacks
    @transport_security_check('admin')
    @authenticated('admin')
    def get(self, *uriargs):
        """
        Parameters: None
        Response: TipsOverviewList
        Errors: None
        """
        tips_complete_list = yield collect_tip_overview()

        self.set_status(200)
        self.finish(tips_complete_list)


class Users(BaseHandler):
    """
    AA

    /admin/overview/users
    """

    @inlineCallbacks
    @transport_security_check('admin')
    @authenticated('admin')
    def get(self, *uriargs):
        """
        Parameters: None
        Response: UsersOverviewList
        Errors: None
        """
        users_complete_list = yield collect_users_overview()

        self.set_status(200)
        self.finish(users_complete_list)


class Files(BaseHandler):
    """
    AB

    /admin/overview/files
    """

    @inlineCallbacks
    @transport_security_check('admin')
    @authenticated('admin')
    def get(self, *uriargs):
        """
        Parameters: None
        Response: FilesOverviewList
        Errors: None
        """

        file_complete_list = yield collect_files_overview()

        self.set_status(200)
        self.finish(file_complete_list)
