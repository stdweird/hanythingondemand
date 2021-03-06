##
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
##
"""

@author: Stijn De Weirdt
"""
import os
import time

from hod.commands.command import ScreenDaemon, RunInScreen
from hod.work.work import Work
from hod.work.hadoop import Hadoop
from hod.config.client import LocalClientOpts, RemoteClientOpts


class LocalClient(LocalClientOpts, Hadoop):
    """This class handles all client config and (if needed) extra services"""
    def __init__(self, ranks, shared):
        Work.__init__(self, ranks)  # don't use Hadoop.__init__, better to redo Hadoop.__init__ with work + opts
        LocalClientOpts.__init__(self, shared)

    def start_work_service_master(self):
        """If the script options is provided, start the screen session"""
        screenname = 'HODclient'
        self.log.debug(
            "Starting screen daemon with screenname %s" % screenname)

        slp = 3

        sd = ScreenDaemon(screenname)
        sd.run()
        time.sleep(slp)

        self.log.debug(
            "Preparing screen client for screen name %s" % screenname)
        sc = RunInScreen(screenname)

        self.log.debug(
            "Source the environment script %s" % self.environment_script)
        sc.run('. %s' % self.environment_script)
        time.sleep(slp)

        if self.shared_opts.get('work_script', None):
            script = os.path.abspath(self.shared_opts['work_script'])
            if os.path.isfile(script):
                sc.run('%s' % script)
                time.sleep(slp)
            else:
                self.log.error("Failed to locate script %s" % script)

            sc.run('echo OK Finished script %s' % script)
            time.sleep(slp)
        else:
            sc.run('echo OK No script run.')
            time.sleep(slp)
        sc.run('echo OK Start client.')
        time.sleep(slp)

    def stop_work_service_master(self):
        """Stop the screen session"""
        self.log.debug("Stopping screen session not implemented")


class RemoteClient(RemoteClientOpts, Hadoop):
    """This class handles all client config and (if needed) extra services"""
    def __init__(self, ranks, shared):
        Work.__init__(self, ranks)  # don't use Hadoop.__init__, better to redo Hadoop.__init__ with work + opts
        RemoteClientOpts.__init__(self, shared)

    def start_work_service_master(self):
        """Start the sshd server"""
        self.log.debug("Starting sshd server")
        self.sshdstart.run()

    def stop_work_service_master(self):
        """Stop the sshd server"""
        self.log.debug("Stopping sshd server")
        self.sshdstop.run()
