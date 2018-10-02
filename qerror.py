#  This file is part of the Qgen utility, a Python package for
#  extending the MyHDL package
#
#  Copyright (C) 2014-2015 Josy Boelen
#
#  The Qgen utility is free software; you can redistribute it and/or
#  modify it under the terms of the GNU Lesser General Public License as
#  published by the Free Software Foundation; either version 3.0 of the
#  License, or (at your option) any later version.
#
#  This utility is distributed in the hope that it will be useful, but
#  WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#  Lesser General Public License for more details.
#
#  You should have received a copy of the GNU Lesser General Public
#  License along with this library; if not, write to the Free Software
#  Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA

'''
Created on 30 Apr 2015

@author: Josy
'''


# definitely need some (nice) error reporting / exception handling
class QError(Exception):
    ''' extending the Exception class '''
    def __init__(self, value, local=False):
        Exception.__init__(self)
        self.value = value
        self.local = local

    def __str__(self):
        return repr(self.value)
