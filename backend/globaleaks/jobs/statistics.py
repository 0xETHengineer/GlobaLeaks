# -*- coding: utf-8 -*-
# Implement collection of statistics
from twisted.internet.defer import inlineCallbacks

from globaleaks.jobs.job import HourlyJob
from globaleaks.models import Stats
from globaleaks.orm import transact
from globaleaks.utils.log import log
from globaleaks.utils.utility import datetime_now


def get_statistics(state):
    stats = {}

    for tid in state.tenant_state:
        stats[tid] = {}
        for e in state.tenant_state[tid].EventQ:
            stats[tid].setdefault(e.event_type, 0)
            stats[tid][e.event_type] += 1

    return stats


@transact
def save_statistics(session, start, stats):
    for tid in stats:
        if not stats[tid]:
            # avoid to save empty stats
            continue

        newstat = Stats()
        newstat.tid = tid
        newstat.start = start
        newstat.summary = stats[tid]
        session.add(newstat)


class Statistics(HourlyJob):
    """
    Statistics collection scheduler run hourly
    """
    monitor_interval = 5 * 60

    def __init__(self):
        HourlyJob.__init__(self)
        self.stats_collection_start_time = datetime_now()

    @inlineCallbacks
    def operation(self):
        current_time = datetime_now()
        statistic_summary = get_statistics(self.state)
        if statistic_summary:
            yield save_statistics(self.state.stats_collection_start_time, statistic_summary)
            log.debug("Stored statistics %s collected from %s to %s",
                      statistic_summary,
                      self.state.stats_collection_start_time,
                      current_time)

        # Hourly Resets
        self.state.reset_hourly()
