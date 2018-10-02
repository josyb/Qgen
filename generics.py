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
Created on  28 Apr 2015
derived from genTcl.py

refactoring everything into classes
splitting a large source file into more manageable pieces

@author: Josy
'''

from __future__ import print_function

import string
import collections

import Utilities.Qgen.qerror as qerror



class Generics(object):
    ''' defining the generics '''

    def __init__(self, genericlist=None):
        self.genericlist = collections.OrderedDict()
        self.section = None
        if genericlist and genericlist != 'Empty':
            for generic in genericlist:
                self.addgeneric(generic[0], generic[1], generic[2] if len(generic) > 2 else False)

    def addsection(self, sectionname):
        value = Section(sectionname)
        self.genericlist.update({sectionname: value})

    def addgeneric(self, key, decl, derived=False):
        if key in self.genericlist:
            raise qerror.QError("Generic / Parameter {} already in dictionary" .format(key))
        if decl[0] == 'Natural':
            value = GenericNatural(key, decl, derived)
        elif decl[0] == 'Boolean':
            value = GenericBoolean(key, decl, derived)
        elif decl[0] == 'String':
            value = GenericString(key, decl, derived)
        else:
            raise qerror.QError('Unhandled Generic \'{}\''.format(decl))

        self.genericlist.update({key: value})

    def value(self, key):
        if key:
            if isinstance(key, str):
                if key in self.genericlist:
                    return self.genericlist[key].value()
                else:
                    return None
            else:
                return key
        else:
            return None

    def isderived(self, key):
        return self.genericlist[key].derived

    def markderived(self, key):
        self.genericlist[key].markderived = True
        
    def show(self):
        print('Generics / Parameters')
        for generic in self.genericlist.values():
            generic.show()

        print()


class Generic(object):
    ''' base class for a generic definition '''

    def __init__(self, name):
        self.name = name
        self.description = None
        self.vhdltype = None
        self.genericvalue = None
        self.allowedranges = None
        self.units = None
        self.derived = False
        self.markderived = False

    def show(self):
        print('{:{width}}Generic: {} : {} := {} -- allowed range: {}, description: {}' \
              .format(' ', self.name, self.vhdltype, self.genericvalue,
                      self.allowedranges, self.description, width=4))

    def value(self):
        return self.genericvalue

    def tclparameter(self, tcltarget):
        for line in ['add_parameter _param_ _type_ _value_\n',
                     'set_parameter_property _param_ DEFAULT_VALUE _value_\n',
                     'set_parameter_property _param_ ALLOWED_RANGES _allowedranges_\n',
                     'set_parameter_property _param_ DISPLAY_HINT boolean\n',
                     'set_parameter_property _param_ DISPLAY_NAME _displayname_\n',
                     'set_parameter_property _param_ TYPE _type_\n',
                     'set_parameter_property _param_ UNITS _units_\n',
                     'set_parameter_property _param_ AFFECTS_ELABORATION true\n',
                     'set_parameter_property _param_ AFFECTS_GENERATION true\n',
                     'set_parameter_property _param_ HDL_PARAMETER false\n',
                     'set_parameter_property _param_ DERIVED true\n',
                     '\n'
                    ]:
            keepline = True
            line = string.replace(line, '_param_', self.name)
            line = string.replace(line, '_type_', self.vhdltype)
            line = string.replace(line, '_value_', '{}'.format(self.genericvalue))
            line = string.replace(line, '_units_', '{}'.format(self.units))
            if self.allowedranges is not None:
                if self.vhdltype == 'natural' or self.vhdltype == 'integer':
                    if isinstance(self.allowedranges, str):
                        ar = self.allowedranges
                    else:
                        ar = ' '
                        for item in self.allowedranges:
                            ar += str(item) + ' '
                            
                    line = string.replace(line, '_allowedranges_', '{{{}}}'.format(ar))
                    
                elif self.vhdltype == 'string':
                    # make the altera required representsation { "if with space"  no_space_in_string ... }
                    line = string.replace(line, '_allowedranges_', '{{ {} }}'.format(self.allowedranges))
                    
                elif self.vhdltype == 'boolean':
                    pass
                
                elif self.vhdltype == 'std_logic_vector':
                    pass
                
                elif self.vhdltype == 'std_logic':
                    pass
                
            else:
                # must delete this line ...
                if '_allowedranges_' in line:
                    keepline = False
                    
            if self.description is not None:
                line = string.replace(line, '_displayname_', '{}'.format(self.description))
            else:
                line = string.replace(line, '_displayname_', self.name)

            if 'DERIVED' in line:
                keepline = self.derived

            if self.vhdltype != 'boolean':
                if 'boolean' in line:
                    keepline = False

            if keepline:
                tcltarget.write(line)

            # add a blank line in between
            tcltarget.write('')

class Section(Generic):
    def __init__(self, sectionname):
        Generic.__init__(self, sectionname)
        self.sectionname = sectionname
        self.derived = True

    def tclparameter(self, tcltarget):
        ''' separate parameter section '''
        tcltarget.write('add_display_item "" "{}" group\n'.format(self.sectionname))


class GenericNatural(Generic):
    def __init__(self, name, decl, derived=False):
        Generic.__init__(self, name)
        self.vhdltype = 'natural'
        self.genericvalue = decl[1]
        self.derived = derived
        if len(decl) > 2:
            self.allowedranges = decl[2]

        if len(decl) > 3:
            self.units = decl[3]

        if len(decl) > 4:
            self.description = decl[4]


    def update(self, argqys):
        self.genericvalue = int(argqys)


class GenericString(Generic):
    def __init__(self, name, decl, derived=False):
        Generic.__init__(self, name)
        self.vhdltype = 'string'
        self.derived = derived
        self.genericvalue = decl[1]
        if len(decl) > 2:
            self.allowedranges = decl[2]

        if len(decl) > 3:
            self.description = decl[3]


    def update(self, argqys):
        self.genericvalue = argqys


class GenericStringList(Generic):
    def __init__(self, name, decl, derived=False):
        Generic.__init__(self, name)
        self.vhdltype = 'stringlist'
        self.genericvalue = decl[0]
        if len(decl) > 1:
            self.allowedranges = decl[1]
        else:
            self.allowedranges = None
        if len(decl) > 2:
            self.description = decl[2]
        else:
            self.description = None
        self.derived = derived

    def update(self, argqys):
        self.genericvalue = argqys


class GenericBoolean(Generic):
    def __init__(self, name, decl, derived=False):
        Generic.__init__(self, name)
        self.vhdltype = 'boolean'
        self.genericvalue = decl[1]
        if len(decl) > 2:
            self.description = decl[2]
        else:
            self.description = None
        self.derived = derived

    def update(self, argqys):
        self.genericvalue = argqys

    def value(self):
        return self.genericvalue == 'true' or self.genericvalue == True


if __name__ == '__main__':
    #''' here we add some tests '''
    pass
