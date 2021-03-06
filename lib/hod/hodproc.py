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
from hod.mpiservice import MpiService

from hod.work.work import TestWorkA, TestWorkB
from hod.work.mapred import Mapred
from hod.work.hdfs import Hdfs
from hod.work.hbase import Hbase
from hod.work.client import LocalClient, RemoteClient


from hod.config.customtypes import HostnamePort, HdfsFs, ParamsDescr
from hod.config.hodoption import HodOption


class Master(MpiService):
    """Basic Master"""

    def distribution(self):
        """Master makes the distribution"""
        # # example part one on half one, part 2 on second half (make sure one is always started)
        self.dists = []

        allranks = range(self.size)
        lim = self.size / 2
        self.dists.append([TestWorkA, allranks[:max(
            lim, 1)]])  # for lim == 0, make sure TestWorkA is started
        self.dists.append([TestWorkB, allranks[lim:]])


class Slave(MpiService):
    """Basic Slave"""
    def __init__(self, options):
        MpiService.__init__(self)
        self.options = options


class HadoopMaster(MpiService):
    """Basic Master Hdfs and MR1"""
    def __init__(self, options):
        MpiService.__init__(self)
        self.options = options

    def distribution(self):
        """Master makes the distribution"""
        self.dists = []

        # # parse the options first
        if self.options.options.hdfs_off:
            self.log.info("HDFS off option set.")
        else:
            self.distribution_HDFS()

        # # if HBase is required, start it before MR; so the MR can use the HBase confs and jars
        if self.options.options.hbase_on:
            self.log.debug("HBase on, starting before MapRed")
            self.distribution_Hbase()

        if self.options.options.mr1_off:
            self.log.info("Mapred off option set.")
        else:
            if self.options.options.yarn_on:
                self.log.info("YARN on option set. Not enabling Mapred")
            else:
                self.distribution_Mapred()

        if self.options.options.yarn_on:
            self.distribution_Yarn()

        # # generate client configs
        self.make_client()

    def make_client(self):
        """Create the client configs"""
        # # recreate the job environment
        if self.options.options.hod_envclass:
            from hod.rmscheduler.hodjob import Job
            job = Job.get_job(self.options.options.hod_envclass, self.options)
            environment = "\n".join(job.generate_environment())
            self.log.debug('Generated environment %s from option hod_envclass %s' % (environment, self.options.options.hod_envclass))
        elif self.options.options.hod_envscript:
            try:
                environment = open(self.options.options.hod_envscript).read()
                self.log.debug('Generated environment %s from option hod_envscript %s' % (environment, self.options.options.hod_envscript))
            except:
                self.log.exception("Failed to read environment script %s" %
                                   self.options.options.hod_envscript)
        else:
            self.log.debug('No environment provided.')
            environment = None

        # # local client config
        shared_localclient = {'environment': environment}
        if self.options.options.hod_script:
            shared_localclient[
                'work_script'] = self.options.options.hod_script
            self.log.debug('set shared work_script from option %s' %
                           self.options.options.hod_script)

        client_ranks = [0]  # only on one rank
        self.dists.append([LocalClient, client_ranks, shared_localclient])

        # # client with socks access
        shared_remoteclient = {'environment': environment}
        client_ranks = [0]  # only on one rank
        self.dists.append([RemoteClient, client_ranks, shared_remoteclient])

    def distribution_HDFS(self):
        """HDFS distribution. Should be one of the first, sets the namenode"""
        network_index = self.select_network()

        # # namenode on rank 0, jobtracker of last one
        nn_rank, hdfs_ranks = self.select_hdfs_ranks()
        nn_param = [HdfsFs(
            "%s:8020" % self.allnodes[nn_rank]['network'][network_index][0]),
            'Namenode on rank %s network_index %s' % (nn_rank, network_index)]

        sharedhdfs = {'params': ParamsDescr({'fs.default.name': nn_param})}
        self.dists.append([Hdfs, hdfs_ranks, sharedhdfs])

    def distribution_Yarn(self):
        """Yarn distribution. Reuse HDFS namenode"""
        self.log.error("Not implemented")

    def distribution_Mapred(self):
        """Mapred distribution. Reuse HDFS namenode"""
        network_index = self.select_network()
        sharedhdfs = None
        for d in self.dists:
            if d[0].__name__ == 'Hdfs':
                sharedhdfs = d[2]
                break
        if sharedhdfs:
            self.log.debug("Found Hdfs work in dists with shared params %s" %
                           (sharedhdfs['params']))
        else:
            self.log.error(
                "No previous Hdfs work found in dists %s" % self.dists)

        jt_rank, mapred_ranks = self.select_mapred_ranks()
        jt_param = [HostnamePort(
            "%s:9000" % self.allnodes[jt_rank]['network'][network_index][0]),
            'Jobtracker on rank %s network_index %s' % (jt_rank, network_index)]

        sharedmapred = {'params': ParamsDescr(
            {'mapred.job.tracker': jt_param})}
        sharedmapred['params'].update(sharedhdfs['params'])
        self.dists.append([Mapred, mapred_ranks, sharedmapred])

    def distribution_Hbase(self):
        """HBase distribution. Reuse HDFS namenode"""
        sharedhdfs = None
        for d in self.dists:
            # # enable hdfs hbase tuning
            d[2].setdefault('other_work', {})
            d[2]['other_work'].setdefault('Hbase', True)
            self.log.debug("Set shared Hbase for %s to true" % d[0].__name__)

            if d[0].__name__ == 'Hdfs':
                sharedhdfs = d[2]

        if sharedhdfs:
            self.log.debug("Found Hdfs work in dists with shared params %s" %
                           (sharedhdfs['params']))
        else:
            self.log.error(
                "No previous Hdfs work found in dists %s" % self.dists)

        hm_rank, hm_ranks = self.select_hbasemaster_ranks()

        sharedhbase = {'params': ParamsDescr({})}
        sharedhbase['params'].update(sharedhdfs['params'])
        self.dists.append([Hbase, hm_ranks, sharedhbase])

    def select_network(self):
        """Given the network info collected in self.allnodes[x]['network'], return the index of the network to use"""

        index = 0  # the networks are ordered by default, use the first one

        self.log.debug("using network index %s" % index)
        return index

    def select_hdfs_ranks(self):
        """return namenode rank and all datanode ranks"""
        allranks = range(self.size)
        rank = allranks[0]

        # # set jt_rank as first rank
        oldindex = allranks.index(rank)
        val = allranks.pop(oldindex)
        allranks.insert(rank, val)

        self.log.debug("Simple hdfs distribution: nn is first of allranks and all slaves are datanode: %s, %s" % (rank, allranks))
        return rank, allranks

    def select_mapred_ranks(self):
        """return jobtracker rank and all tasktracker ranks"""
        allranks = range(self.size)
        rank = allranks[0]

        # # set jt_rank as first rank
        oldindex = allranks.index(rank)
        val = allranks.pop(oldindex)
        allranks.insert(rank, val)

        self.log.debug("Simple mapred distribution: jt is first of allranks and all slaves are tasktracker: %s , %s" % (rank, allranks))
        return rank, allranks

    def select_hbasemaster_ranks(self):
        """return hbasemaster/zookeeper rank and all regionservers ranks"""
        allranks = range(self.size)
        rank = allranks[0]

        # # set jt_rank as first rank
        oldindex = allranks.index(rank)
        val = allranks.pop(oldindex)
        allranks.insert(rank, val)

        self.log.debug("Simple hbase distribution: hm is first of allranks and all slaves are regioserver: %s , %s" % (rank, allranks))
        return rank, allranks
