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
@author: Ewan Higgs
"""
import re
import os
import socket
import logging as log
import netifaces
import netaddr
import struct
import multiprocessing

from vsc.utils.affinity import sched_getaffinity

from vsc import fancylogger
_log = fancylogger.getLogger(fname=False)

def netmask2maskbits(netmask):
    """Find the number of bits in a netmask."""
    mask_as_int = netaddr.IPAddress(netmask).value
    return bin(mask_as_int).count('1')


def get_networks():
        """
        Returns list of network information by interface.
        Of the form: [hostname, ipaddr, iface, subnetmask]
        """
        devices = netifaces.interfaces()
        networks = []
        for device in devices:
            iface = netifaces.ifaddresses(device)
            if netifaces.AF_INET in iface:
                iface = iface[netifaces.AF_INET][0]
                addr = iface['addr']
                netmask = iface['netmask']
                mask_bits = netmask2maskbits(iface['netmask'])
                hostname = socket.getfqdn(addr) # socket.gethostbyaddr(addr)[0] # used this before.
                networks.append([hostname, addr, device, mask_bits])
        return networks


def address_in_network(ip, net):
    """
    Determine if an ip is in a network.
    e.g. 192.168.0.1 is in 192.168.0.0/24 but not 10.0.0.0/24.

    Params
    ------
    ip :    str`
    ipv4 ip address as string.

    net : `str`
    Network and mask bits as string (e.g. '192.168.0.0/16')
    """
    return netaddr.IPAddress(ip) in netaddr.IPNetwork(net)

def ip_interface_to(networks, ip):
    """Which of the detected network interfaces can reach ip"""
    for intf in networks:
        net = "%s/%s" % (intf[1], intf[3])
        if address_in_network(ip, net):
            return intf
    return None


def _sorted_network(network):
    """Try to find a preferred network (can be advanced like IPoIB of high-speed ethernet)"""
    nw = []
    _log.debug("Preferred network selection")
    # # step 1 alphabetical ordering (who knows in what order ip returns the addresses) on hostname field
    network.sort()

    # # look for ib network
    ib_reg = re.compile("^(ib)\d+$")
    for intf in network:
        if ib_reg.search(intf[2]):
            if not intf in nw:
                _log.debug("Added intf %s as ib interface" % intf)
                nw.append(intf)

    # # final selection prefer non-vlan
    vlan_reg = re.compile("^(.*)\.\d+$")
    loopback_reg = re.compile("^(lo)\d*$")
    for intf in network:
        if not (vlan_reg.search(intf[2]) or loopback_reg.search(intf[2])):
            if not intf in nw:
                _log.debug("Added intf %s as non-vlan or non-loopback interface" % intf)
                nw.append(intf)

    # # add remainder non-loopback
    for intf in network:
        if not loopback_reg.search(intf[2]):
            if not intf in nw:
                _log.debug("Added intf %s as remaining non-loopback interface" % intf)
                nw.append(intf)

    # # add remainder
    for intf in network:
        if not intf in nw:
            _log.debug("Added intf %s as remaining interface" % intf)
            nw.append(intf)

    _log.debug("ordered network %s" % nw)
    return nw

def get_memory():
    """Extract information about the available memory"""
    memory = {}
    memory['meminfo'] = {}
    re_mem = re.compile(r"^\s*(?P<mem>\d+)(?P<unit>(?:k)B)?\s*$")
    proc_meminfo_fn = '/proc/meminfo'
    for line in open(proc_meminfo_fn).read().replace(' ', '').split('\n'):
        if not line.strip():
            continue
        key = line.split(':')[0].lower().strip()
        try:
            value = line.split(':')[1].strip()
        except IndexError:
            log.error("No :-separated entry for line %s in %s" %
                           (line, proc_meminfo_fn))
            continue
        reg = re_mem.search(value)
        if reg:
            unit = reg.groupdict()['unit']
            mem = int(reg.groupdict()['mem'])
            multi = 1
            if unit in (None, 'B',):
                multi = 1
            elif unit in ('kB',):
                multi = 2 ** 10
            else:
                log.error("Unsupported memory unit %s in key %s value %s" % (unit, key, value))
            memory['meminfo'][key] = mem * multi
        else:
            log.error("Unknown memory entry in key %s value %s" % (key, value))

    log.debug("Collected meminfo %s" % memory['meminfo'])
    return memory


class Node(object):
    """Detect localnode properties"""
    def __init__(self):
        self.log = fancylogger.getLogger(name=self.__class__.__name__, fname=False)
        self.fqdn = 'localhost' # base fqdn hostname
        self.network = [] # all possible IPs

        self.pid = -1
        self.cores = -1
        self.usablecores = None

        self.topology = [0] # default topology plain set

        self.memory = {}

    def __str__(self):
        return "FQDN %s PID %s" % (self.fqdn, self.pid)

    def go(self):
        """A wrapper around some common functions"""
        self.fqdn = socket.getfqdn()
        self.network = _sorted_network(get_networks())

        self.pid = os.getpid()
        self.usablecores = [idx for idx, used in enumerate(sched_getaffinity().cpus) if used]
        self.cores = len(self.usablecores)

        self.memory = get_memory()

        descr = {
            'fqdn': self.fqdn,
            'network': self.network,
            'pid': self.pid,
            'cores': self.cores,
            'usablecores': self.usablecores,
            'topology': self.topology,
            'memory': self.memory,
        }
        return descr
