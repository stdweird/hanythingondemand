# #
# Copyright 2009-2013 Ghent University
#
# This file is part of hanythingondemand
# originally created by the HPC team of Ghent University (http://ugent.be/hpc/en),
# with support of Ghent University (http://ugent.be/hpc),
# the Flemish Supercomputer Centre (VSC) (https://vscentrum.be/nl/en),
# the Hercules foundation (http://www.herculesstichting.be/in_English)
# and the Department of Economy, Science and Innovation (EWI) (http://www.ewi-vlaanderen.be/en).
#
# http://github.com/hpcugent/hanythingondemand
#
# hanythingondemand is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation v2.
#
# hanythingondemand is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with hanythingondemand. If not, see <http://www.gnu.org/licenses/>.
# #
"""

@author: Stijn De Weirdt
"""
from vsc import fancylogger


import time
import os
import tempfile

from hod.mpiservice import MpiService, barrier, MASTERRANK


class Work(object):
    """Basic work class"""
    def __init__(self):
        self.log = fancylogger.getLogger(self.__class__.__name__, fname=False)
        self.svc = MpiService(log=self.log)

        self.work_max_age = 3600 * 71
        self.work_start_time = time.time()

        self.controldir = None

    def prepare_work_cfg(self):
        """prepare any config"""
        self.log.error("Not implemented prepare_work_cfg.")

    def pre_start_work_service(self):
        """Run pre-start jobs for service."""

    def start_work_service(self):
        """Start service"""
        self.log.error("Not implemented start_work_service_master.")

    def stop_work_service(self):
        """Stop the service"""
        self.log.debug("Not implemented stop_work_service_master.")

    def work_wait(self):
        """What to do between start and stop (and how stop is triggered). Returns True is the wait is over"""
        now = time.time()
        if (now - self.work_start_time) > self.work_max_age:
            self.log.debug("Work started at %s, now is %s, which is more then max_age %s" % (time.localtime(self.work_start_time), time.localtime(now), self.work_max_age))
            return True  # wait is over

    def do_work_start(self):
        """Start the work"""
        barrier(self.svc.comm, "Going to run pre-start work on rank %s" % self.svc.rank)
        self.pre_start_work_service()
        barrier(self.svc.comm, "Going to start work on rank %s" % self.svc.rank)
        self.start_work_service()

    def do_work_wait(self):
        barrier(self.svc.comm, "Going to wait work on all. Return True when all is over")

        ans = self.work_wait()  # True when wait is over

        # # override mechanisms
        force_fn = os.path.join(self.controldir, 'force_stop')
        if os.path.isfile(force_fn):
            self.log.warn(
                "Force stop detected. work_wait was %s. return True" % ans)
            return True
        else:
            self.log.debug("No force stop file %s found" % force_fn)

        force_fn = os.path.join(self.controldir, 'force_continue')
        if os.path.isfile(force_fn):
            self.log.warn("Force continue detected. work_wait was %s. return False" % ans)
            return False
        else:
            self.log.debug("No force continue file %s found" % force_fn)

        return ans

    def do_work_stop(self):
        """Start the work"""
        self.pre_run_any_service()

        barrier(self.svc.comm, "Going to stop work on ")
        self.stop_work_service()
