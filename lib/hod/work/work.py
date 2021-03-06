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

from hod.mpiservice import MpiService


class Work(MpiService):
    """Basic work class"""
    def __init__(self, ranks, shared=None):
        self.log = fancylogger.getLogger(self.__class__.__name__, fname=False)
        MpiService.__init__(self, initcomm=False, log=self.log)

        self.shared_work = shared  # shared is something that can be shared between work (eg common information)
        self.log.debug("shared_work %s" % self.shared_work)

        self.allranks = ranks

        self.commands = {}  # dict with command : list of ranks

        self.work_max_age = 3600 * 71
        self.work_start_time = time.time()

        self.controldir = tempfile.mkdtemp()

    def pre_run_any_service(self):
        """To be run before any service"""

    def post_run_any_service(self):
        """To be run before any service"""

    def run(self, comm):
        """Setup MPI comm and do_work"""
        self.work_begin(comm)
        self.do_work()
        self.work_end()

    def prepare_work_cfg(self):
        """prepare any config"""
        self.log.error("Not implemented prepare_work_cfg.")

    def work_begin(self, comm):
        """Prepartion of work, previous to start"""
        self.init_comm(comm, startwithbarrier=True)

        self.log.debug("run do_work")

        self.prepare_work_cfg()

    def work_end(self):
        """Cleanup work"""
        self.stop_service()

    def start_work_service_master(self):
        """Start service on master only"""
        self.log.error("Not implemented start_work_service_master.")

    def start_work_service_slaves(self):
        """Start service on slaves only"""
        self.log.debug("Not implemented start_work_service_slaves.")

    def start_work_service_all(self):
        """Run start_service on all"""
        self.log.debug("Not implemented start_work_service_all.")

    def stop_work_service_master(self):
        """Stop the Hadoop service on master only"""
        self.log.debug("Not implemented stop_work_service_master.")

    def stop_work_service_slaves(self):
        """Stop the Hadoop service on slaves only"""
        self.log.debug("Not implemented stop_work_service_slaves.")

    def stop_work_service_all(self):
        """Run after start_service"""
        self.log.debug("Not implemented stop_work_service_all.")

    def work_wait(self):
        """What to do between start and stop (and how stop is triggered). Returns True is the wait is over"""
        now = time.time()
        if (now - self.work_start_time) > self.work_max_age:
            self.log.debug("Work started at %s, now is %s, which is more then max_age %s" % (time.localtime(self.work_start_time), time.localtime(now), self.work_max_age))
            return True  # wait is over

    def do_work(self):
        """Look for required code and prepare all"""
        self.log.debug("Do work start")
        self.do_work_start()
        self.do_work_wait()
        self.do_work_stop()
        self.log.debug("Do work end")

    def do_work_start(self):
        """Start the work"""
        self.pre_run_any_service()
        self.barrier("Going to start work on master only and on slaves only")
        if self.rank == self.masterrank:
            self.start_work_service_master()
        if self.rank != self.masterrank or self.size == 1:
            # # slaves and in case there is only one node (master=slave)
            self.start_work_service_slaves()
        self.barrier("Going to start work on all")
        self.start_work_service_all()
        self.post_run_any_service()

    def do_work_wait(self):
        self.pre_run_any_service()
        self.barrier("Going to wait work on all. Return True when all is over")

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

        self.post_run_any_service()
        return ans

    def do_work_stop(self):
        """Start the work"""
        self.pre_run_any_service()

        self.barrier("Going to stop work on all")
        self.stop_work_service_all()

        self.barrier("Going to stop work on master only and on lsaves only")
        if self.rank == self.masterrank:
            self.stop_work_service_master()
        if self.rank != self.masterrank or self.size == 1:
            # # slaves and in case there is only one node (master=slave)
            self.stop_work_service_slaves()
        self.post_run_any_service()


class SleepWork(Work):
    def do_work(self):
        """Just sleep"""
        sleeptime = 3
        self.log.debug("do_work: sleep %d" % sleeptime)

        import time
        time.sleep(sleeptime)

        self.log.debug("do_work: end sleep %d" % sleeptime)


class TestWorkA(SleepWork):
    """TestWorkA for testing"""


class TestWorkB(SleepWork):
    """TestWorkB for testing"""
