from hod.commands.command import JavaVersion
from hod.commands.hadoop import HadoopVersion

import os, re

from vsc import fancylogger
fancylogger.setLogLevelDebug()

class HadoopCfg:
    """Hadoop cfg class. Environment and xml cfg control"""
    def __init__(self):
        self.log = fancylogger.getLogger(self.__class__.__name__)

        self.version = {'major':-1,
                        'minor':-1,
                        'small':-1,
                        'suffix': None,
                        }

        self.hadoophome = None # hadoop home
        self.hadoop = None

        self.javaversion = {'major':-1,
                            'minor':-1,
                            'suffix': None,
                            }
        self.java = None
        self.javahome = None

        self.name = 'all' ## default task start-all.sh, stop-all.sh
        self.start = None
        self.stop = None

        self.extrasearchpaths = []

    def run(self):
        """Perform configuration gathering"""
        ## some default initialisation
        self.log.debug("Starting cfg preparation for name %s" % self.name)
        self.prep_java()
        self.prep_hadoop()
        self.locate_start_stop()

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
            vals.pop(0) ## empty
        vals.insert(0, value)
        newvalue = ':'.join(vals)
        os.environ[variable] = newvalue
        self.log.debug("set new value of variable %s to %s" % (variable, newvalue))

    def setenv(self, variable, value):
        """Set (ie override if needed) variable to value"""
        os.environ[variable] = value
        self.log.debug("set new value of variable %s to %s" % (variable, value))

    def which_java(self):
        """Locate java and/or JAVA_HOME"""
        java = self.which_exe('java')
        ## is JAVA_HOME set?
        javahome = os.environ.get('JAVA_HOME', None)
        if javahome and not os.path.isdir(javahome):
            self.log.error("JAVA_HOME %s not a directory" % javahome)
            javahome = None

        if java:
            self.log.debug("java found %s" % java)
            if javahome and (not java == os.path.join(javahome, 'bin', 'java')):
                self.log.error("java %s does not match JAVA_HOME/bin/java (JAVA_HOME %s)" % (java, javahome))
                ## java from JAVA_HOME takes precedence
                java = os.path.join(javahome, 'bin', 'java')
                self.addenv('PATH', os.path.dirname(java))
        else:
            self.log.error('java not found in path.')
            if javahome:
                java = os.path.join(javahome, 'bin', 'java')
                if os.path.isfile(java):
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
        self.java, self.javahome = self.which_java() ## after which_java is java in PATH
        self.setenv('JAVA_HOME', self.javahome) ## required for Hadoop
        self.java_version()

    def which_hadoop(self):
        """Locate HADOOP_HOME and hadoop"""
        self.hadoop = self.which_exe('hadoop')
        self.hadoophome = self.which_exe('hadoop', stripbin=True)

    def hadoop_version(self):
        """Set the major and minor version"""
        hv = HadoopVersion()
        hv_out, hv_err = hv.run()

        hadoopVerRegExp = re.compile("^\s*Hadoop\s+(\d+)\.(\d+)(?:\.(\d+)(?:(?:-|_)(\S+))?)?\s*$", re.M)
        verMatch = hadoopVerRegExp.search(hv_out)
        if verMatch:
            self.version['major'] = int(verMatch.group(1))
            self.version['minor'] = int(verMatch.group(2))
            if verMatch.group(3):
                self.version['small'] = int(verMatch.group(3))
            if verMatch.group(4):
                self.version['suffix'] = verMatch.group(4)
            self.log.debug('Version found from hadoop command: %s' % self.version)
        else:
            self.log.error("No Hadoop version found (output %s err %s)" % (hv_out, hv_err))

    def prep_hadoop(self):
        """Check and prepare hadoop environment"""
        self.which_hadoop()
        self.hadoop_version()

    def locate_start_stop(self):
        """Try to locate the start and stop scripts"""
        startname = "start-%s.sh" % self.name
        stopname = "start-%s.sh" % self.name

        searchpaths = [os.path.join(self.hadoophome, 'sbin'), os.path.join(self.hadoophome, 'bin')] + self.extrasearchpaths

        for path in searchpaths:
            fn = os.path.join(path, startname)
            if os.path.isfile(fn):
                self.start = fn
                self.log.debug("Found start %s for name %s" % (self.start, self.name))
                break
        if self.start is None:
            self.log.error("start for name %s not found in paths %s" % (self.name, searchpaths))

        for path in searchpaths:
            fn = os.path.join(path, stopname)
            if os.path.isfile(fn):
                self.stop = fn
                self.log.debug("Found stop %s for name %s" % (self.stop, self.name))
                break
        if self.start is None:
            self.log.error("start for name %s not found in paths %s" % (self.name, searchpaths))

    def is_version_ok(self, req=None):
        """Given a requirement req, check if current version is sufficient"""

