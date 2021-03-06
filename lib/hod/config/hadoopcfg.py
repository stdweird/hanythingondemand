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
import os
from os.path import isfile
import re

from hod.commands.command import JavaVersion
from hod.commands.hadoop import HadoopVersion

from vsc.utils import fancylogger


class HadoopCfg:
    """Hadoop cfg class. Environment and xml cfg control"""
    def __init__(self):
        self.log = fancylogger.getLogger(self.__class__.__name__, fname=False)

        self.hadoopversion = {
            'major':-1,
            'minor':-1,
            'small':-1,
            'suffix': None,
        }

        self.hadoophome = None  # hadoop home (could be $EBROOTHADOOP)
        self.hadoop = None

        self.javaversion = {
            'major':-1,
            'minor':-1,
            'suffix': None,
        }
        self.java = None
        self.javahome = None

        self.name = 'all'  # default task start-all.sh, stop-all.sh
        self.daemonname = 'hadoop'

        self.start_script = None
        self.stop_script = None
        self.daemon_script = None

        self.extrasearchpaths = []

    def basic_cfg(self):
        """Perform configuration gathering"""
        # # some default initialisation
        self.log.debug("Starting cfg preparation for name %s" % self.name)
        self.prep_java()
        self.prep_hadoop()
        self.basic_cfg_extra()
        self.locate_start_stop_daemon()

    def basic_cfg_extra(self):
        """Perform extra configuration gathering"""
        self.log.debug("basic_cfg_extra not implemented")

    def which_exe(self, exe, showall=False, stripbin=False):
        """Locate executable exe (similar to which). If all is True, return list of all found executables.
        stripbin: return the base directory when /bin is found (eg /usr/bin/exe will return /usr)"""
        allpaths = []

        defpaths = os.environ.get('PATH', '').split(':') + ['/usr/local/bin', '/usr/bin', '/usr/sbin', '/bin', '/sbin']
        for p in defpaths:
            p = os.path.abspath(p).rstrip('/')
            location = os.path.join(p, exe)
            if os.path.exists(location):
                if stripbin:
                    if p.endswith('/bin'):
                        location = '/'.join(p.split('/')[:-1])
                    else:
                        self.log.error("Which exe %s found %s, but does not end with bin (stripbin %s). Continue." % (exe, location, stripbin))
                        continue
                if showall:
                    allpaths.append(location)
                else:
                    self.log.debug("which exe %s returns %s (stripbin %s)" % (exe, location, stripbin))
                    return location
        if showall and len(allpaths) > 0:
            self.log.debug("which exe %s returns all %s (stripbin %s)" % (exe, allpaths, stripbin))
            return allpaths
        else:
            self.log.error("Failed to locate executable %s in paths %s. Returning None" % (exe, defpaths))
            return None

    def addenv(self, variable, value):
        """Add value to (non-)existing variable"""
        vals = os.environ.get(variable, '').split(':')
        if not vals[0]:
            vals.pop(0)  # empty due to empty string
        vals.insert(0, "%s" % value)  # to string due to derived types
        newvalue = ':'.join(vals)
        os.environ[variable] = newvalue
        self.log.debug("addenv: set new value of variable %s to %s after adding %s" % (variable, newvalue, value))

    def setenv(self, variable, value):
        """Set (ie override if needed) variable to value"""
        prevvalue = os.environ.get(variable, '')
        os.environ[variable] = value
        self.log.debug("setenv: set new value of variable %s to %s (previous: %s)" % (variable, value, prevvalue))

    def which_java(self):
        """Locate java and/or JAVA_HOME"""
        java = self.which_exe('java')
        # # is JAVA_HOME set?
        javahome = os.environ.get('JAVA_HOME', None)
        if javahome and not os.path.isdir(javahome):
            self.log.error("JAVA_HOME %s not a directory" % javahome)
            javahome = None

        if java:
            self.log.debug("java found %s" % java)
            if javahome and (not java == os.path.join(javahome, 'bin', 'java')):
                self.log.warn("java %s does not match JAVA_HOME/bin/java (JAVA_HOME %s)" % (java, javahome))
                # # java from JAVA_HOME takes precedence
                java = os.path.join(javahome, 'bin', 'java')
                self.addenv('PATH', os.path.dirname(java))
        else:
            self.log.error('java not found in path.')
            if javahome:
                java = os.path.join(javahome, 'bin', 'java')
                if isfile(java):
                    self.log.debug("java %s located from JAVA_HOME" % java)
                    self.addenv('PATH', os.path.dirname(java))
                else:
                    self.log.error("no java %s located from JAVA_HOME %s" % (java, javahome))
                    java = None

        if javahome:
            if java and not javahome == '/'.join(java.split('/')[:-2]):
                self.log.error("javahome %s does not match parent of basedir of java %s" % (javahome, java))
                javahome = None
        if java:
            if javahome:
                self.log.debug("Found java %s and javahome %s" % (java, javahome))
                self.setenv('JAVA_HOME', javahome)
                return java, javahome
            else:
                javahome = self.which_exe('java', stripbin=True)
                if javahome:
                    self.log.debug("Found java %s and javahome %s" % (java, javahome))
                    return java, javahome
                else:
                    self.log.error("which could locate javahome with stripbin")

    def java_version(self):
        """Determine java version"""
        jv = JavaVersion()
        jv_out, jv_err = jv.run()
        javaVerRegExp = re.compile("^\s*java\s+version\s+(?:\'|\")?(\d+)\.(\d+)(?:\.(\d+)(?:(?:-|_)(\S+))?)?(?:\'|\")?\s*$", re.M)
        verMatch = javaVerRegExp.search(jv_out)
        if verMatch:
            self.javaversion['major'] = int(verMatch.group(1))
            self.javaversion['minor'] = int(verMatch.group(2))
            if verMatch.group(3):
                self.javaversion['suffix'] = int(verMatch.group(3))
            if verMatch.group(4):
                self.javaversion['suffix'] = verMatch.group(4)
            self.log.debug('Version found from java command: %s' % self.javaversion)
        else:
            self.log.error("No java version found (output %s err %s)" % (jv_out, jv_err))

    def prep_java(self):
        """Prepare and verify java environment"""
        self.java, self.javahome = self.which_java()  # after which_java is java in PATH
        self.setenv('JAVA_HOME', self.javahome)  # required for Hadoop
        self.java_version()

    def which_hadoop(self):
        """Locate HADOOP_HOME and hadoop"""
        self.hadoop = self.which_exe('hadoop')
        self.hadoophome = self.which_exe('hadoop', stripbin=True)

    def hadoop_version(self):
        """Set the major and minor hadoopversion"""
        hv = HadoopVersion()
        hv_out, hv_err = hv.run()

        hadoopVerRegExp = re.compile("^\s*Hadoop\s+(\d+)\.(\d+)(?:\.(\d+)(?:(?:-|_)(\S+))?)?\s*$", re.M)
        verMatch = hadoopVerRegExp.search(hv_out)
        if verMatch:
            self.hadoopversion['major'] = int(verMatch.group(1))
            self.hadoopversion['minor'] = int(verMatch.group(2))
            if verMatch.group(3):
                self.hadoopversion['small'] = int(verMatch.group(3))
            if verMatch.group(4):
                self.hadoopversion['suffix'] = verMatch.group(4)
            self.log.debug('Version found from hadoop command: %s' % self.hadoopversion)
        else:
            self.log.error("No Hadoop hadoopversion found (output %s err %s)" % (hv_out, hv_err))

    def prep_hadoop(self):
        """Check and prepare hadoop environment"""
        self.which_hadoop()
        self.hadoop_version()

    def locate_start_stop_daemon(self):
        """Try to locate the start, stop and daemon scripts"""
        startname = "start-%s.sh" % self.name
        stopname = "stop-%s.sh" % self.name
        daemonname = "%s-daemon.sh" % self.daemonname

        searchpaths = [
                os.path.join(self.hadoophome, 'sbin'), 
                os.path.join(self.hadoophome, 'bin'), 
                os.path.join(self.hadoophome, 'bin-mapreduce1'),
                ] + self.extrasearchpaths

        def _files_in_path(path, files):
            return all([isfile(os.path.join(path, f)) for f in files])

        # If we find all 3 files together, use them together. This is the case with bin-mapreduce1
        for path in searchpaths:
            if _files_in_path(path, [startname, stopname, daemonname]):
                self.start_script = os.path.join(path, startname)
                self.stop_script = os.path.join(path, stopname)
                self.daemon_script = os.path.join(path, daemonname)

        # If they weren't found together, look them up.
        if self.start_script is None:
            for path in searchpaths:
                startpath = os.path.join(path, startname)
                if self.start_script is None and isfile(startpath):
                    self.start_script = startpath
                    self.log.debug("Found start_script %s for name %s" % (self.start_script, self.name))

                stoppath = os.path.join(path, stopname)
                if self.stop_script is None and isfile(stoppath):
                    self.stop_script = stoppath
                    self.log.debug("Found stop_script %s for name %s" % (self.stop_script, self.name))

                daemonpath = os.path.join(path, daemonname)
                if self.daemon_script is None and isfile(daemonpath):
                    self.daemon_script = daemonpath
                    self.log.debug("Found daemon_script %s for name %s daemonname %s" % (self.daemon_script, self.name, self.daemonname))

        if self.start_script is None:
            self.log.error("start_script %s for name %s not found in paths %s" % (startname, self.name, searchpaths))

        if self.start_script is None:
            self.log.error("start_script %s for name %s not found in paths %s" % (stopname, self.name, searchpaths))

        if self.daemon_script is None:
            self.log.error("daemon_script %s for name %s daemonname %s not found in paths %s" % (daemonname, self.name, self.daemonname, searchpaths))

    def is_version_ok(self, req=None):
        """Given a requirement req, check if current hadoopversion is sufficient"""
