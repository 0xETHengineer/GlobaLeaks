# -*- coding: utf-8

from twisted.internet.defer import inlineCallbacks

from globaleaks.jobs.job import HourlyJob
from globaleaks.state import State
from globaleaks.utils.log import log


__all__ = ['ExitNodesRefresh']


class ExitNodesRefresh(HourlyJob):
    @inlineCallbacks
    def operation(self):
        net_agent = self.state.get_agent()
        log.debug('Fetching list of Tor exit nodes')
        yield State.tor_exit_set.update(net_agent)
        log.debug('Retrieved a list of %d exit nodes', len(State.tor_exit_set))
