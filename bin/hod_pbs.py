#!/usr/bin/env python
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
Generate a PBS job script using pbs_python. Will use mympirun to get the all started

@author: Stijn De Weirdt (Universiteit Gent)
@author: Ewan Higgs (Universiteit Gent)
"""

import sys
from hod.rmscheduler.hodjob import PbsEBMMHod, MympirunHodOption

def main(args):
    options = MympirunHodOption(go_args=args)
    j = PbsEBMMHod(options)
    j.run()

if __name__ == '__main__':
    sys.exit(main(sys.argv))
