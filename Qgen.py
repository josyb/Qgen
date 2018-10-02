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

import sys
import os
import argparse

import myhdl

import Utilities.Qgen.generics as generics
import Utilities.Qgen.connectionpoints as connectionpoints
import Utilities.Qgen.generate as generate
import Utilities.Qgen.qerror as qerror


class Qgen(object):
    ''' the worker class
        reduces the overhead in the module to a few (more or less) simple lines
    '''

    def __init__(self,
                 modulename,
                 genericlist=None,
                 connectionpointlist=None,
                 testbench=None,  # args: (time, tb_modulename)
                 convert=None,  # args: (targetHDL) -- 'vhdl' or 'verilog'
                 elaborate=None,  # args: [PARAM1 value1 PARAM2 value2 ...]
                 gentcl=False  # args: version, author, group
                 ):
        self.modulename = modulename
        self.testbench = testbench
        self.convert = convert
        self.elaborate = elaborate
        self.gentcl = gentcl
        # parsing arguments with argparse takes some learning,
        # but is handy especially as the usage() and help is generated for you ...
        parser = argparse.ArgumentParser(description=modulename)
        parser.add_argument('-v', '--verbose', action='store_true',
                            help='Verbose - print out what happens along the way')
        parser.add_argument('-e', '--QsysElaborate', nargs='*')
        parser.add_argument('-g', '--QsysGenerate', nargs='*')
        parser.add_argument('-l', '--targetHDL', type=str, default=None)
        parser.add_argument('-i', '--ignoreQsys', action='store_true')
        self.args = parser.parse_args()

        if self.args.verbose:
            print("Arguments: {}" .format(self.args))

        #  'catch' the Qsys Elaboration call
        if self.args.QsysElaborate and not self.args.ignoreQsys:
            if self.args.verbose:
                print('QsysElaborate')
            if self.elaborate is not None:
                # qsysarguments contains all the parameters with the currently assigned values (in the Qsys GUI)
                # use a dictionary to pair the arguments
                qsysargdict = {}
                for name, value in zip(self.args.QsysElaborate[0::2], self.args.QsysElaborate[1::2]):
                    qsysargdict[name] = value

                print(self.elaborate(qsysargdict), file=sys.stdout)
                sys.exit(0)
            else:
                print("No Elaboration function given!")
                return None

        if genericlist:
            self.generics = generics.Generics(genericlist)
            # must update generics with values from Qsys before building connection points
            if self.args.QsysGenerate and not self.args.ignoreQsys:
                # Qsys calling on us to generate
                if self.args.verbose:
                    # redirect the console output to a log-file
                    redirect = open('{}.log'.format(modulename), 'w')
                    sys.stdout = redirect
                    sys.stderr = redirect
                    # tell us all about it
                    print(sys.version)
                    print("Qsys arguments: {}" .format(self.args.QsysGenerate))

                # update the generics
                for key, value in zip(self.args.QsysGenerate[2::2], self.args.QsysGenerate[3::2]):
                    self.generics.genericlist['{}'.format(key)].update(value)

            if connectionpointlist:
                self.connectionpointlist = connectionpoints.ConnectionPoints(self.generics, connectionpointlist)
                self.run()

        else:
            self.generics = generics.Generics()
            self.connectionpointlist = connectionpoints.ConnectionPoints()

    def run(self):
        # can now either generate or simulate/convert/generateTcl
        if self.args.QsysGenerate and not self.args.ignoreQsys:
            if self.args.verbose:
                print('Generating {} for Qsys' .format(self.args.targetHDL))
            # force std_logic_vectors instead of unsigned in Interface as Qsys wants this
            myhdl.toVHDL.std_logic_ports = True
            self.convert(self, 'vhdl')  # override self.args.targetHDL as this is 'always'verilog?
            # rename the entity and architecture identifiers to match the name given by Qsys
            generate.updateEntity("{}" .format(self.modulename), self.args.QsysGenerate[1])
            # delete existing target
            target = "{}{}.vhd" .format(self.args.QsysGenerate[0], self.args.QsysGenerate[1])
            if os.path.exists(target):
                os.remove(target)
            os.rename("{}.vhd".format(self.modulename), target)
        else:
            if self.args.verbose:
                print('Simulate, Convert, Generate _hw.tcl')
            if self.testbench:
                # remove 'old' .vcd file
                filename = self.testbench[1].__name__ + ".vcd"
                if os.access(filename, os.F_OK):
                    os.unlink(filename)

                # Run Simulation
                testbench = myhdl.traceSignals(self.testbench[1], self)

                sim = myhdl.Simulation(testbench)
                sim.run(self.testbench[0])

            if self.convert:
                if self.args.targetHDL is not None:
                    self.convert(self, self.args.targetHDL)
                else:
                    # do both languages
                    self.convert(self, 'vhdl')
                    self.convert(self, 'verilog')

            if self.gentcl:
                generate.writeHwTcl(self.generics, self.connectionpointlist, self.modulename,
                                    version=self.gentcl[0],
                                    author=self.gentcl[1],
                                    group=self.gentcl[2])

    def addgenericlist(self, genericlist):
        self.generics = generics.Generics(genericlist)

    def addsection(self, section):
        self.generics.addsection(section)

    def addgeneric(self, decl, derived=False):
        self.generics.addgeneric(decl[0], decl[1], derived)

#     def updategenerics(self):
#         for key, value in zip(self.args.QsysGenerate[0::2], self.args.QsysGenerate[1::2]):
#             self.generics['{}'.format(key)].update(value)

    def genericvalue(self, key):
        return self.generics.value(key)

    def widthempty(self, key):
        return self.connectionpointlist.widthempty(key)

    def widthchannel(self, key):
        return self.connectionpointlist.widthchannel(key)

    def connectionpoints(self, connectionpointlist):
        self.connectionpointlist = connectionpoints.ConnectionPoints(self.generics, connectionpointlist)

    def addconectionpoint(self, decl):
        self.connectionpointlist.addconnectionpoint(decl)

    def addclock(self, name, frequency=0):
        self.connectionpointlist.addclock(name, frequency)

    def addreset(self, name, associatedclock=None, edges=None):
        self.connectionpointlist.addreset(name, associatedclock, edges)

    def addclockreset(self, clk, reset, frequency=0, edges=None):
        self.connectionpointlist.addclock(clk, frequency)
        self.connectionpointlist.addreset(reset, clk, edges)

    def addsinksource(self, sinkorsource, name, associatedclockreset, data,
                      packets=None, channel=None, error=None):
        self.connectionpointlist.addsinksource(sinkorsource, name, associatedclockreset, data,
                                               packets, channel, error)

    def addMMSlaveMaster(self, slaveormaster, name, associatedclockreset, address,
                         burst=None, width=32, writedesc=None, readdesc=None, waitrequest=None,
                         readdatavalid=None, setuptime=None, bridgestomaster=None):
        self.connectionpointlist.addMMSlaveMaster(slaveormaster, name, associatedclockreset, address,
                                                  burst, width, writedesc, readdesc, waitrequest,
                                                  readdatavalid, setuptime, bridgestomaster)

    def addConduit(self, name, associatedclockreset, signals):
        self.connectionpointlist.addConduit(name, associatedclockreset, signals)

    def makesignals(self, interface):
        return self.connectionpointlist.makesignals(interface)

    def makeinterface(self, interface):
        pass
#     def interfacesignals(self, interface):
#         return self.connectionpointlist.interfacesignals(interface)

    def GenTcl(self, gentcl):
        generate.writeHwTcl(self.generics, self.connectionpointlist, self.modulename,
                            version=gentcl[0], author=gentcl[1], group=gentcl[2])

    def show(self):
        self.generics.show()
        self.connectionpointlist.show()


if __name__ == '__main__':
    # ''' here we add some tests '''

    try:
        g = Qgen('testQsys',
                 # parameters
                 (('WIDTH_D', ('Natural', 12, (8, 12, 16), 'bits')),
                  ('USE_PACKETS_D', ('Boolean', True)),
                  ('WIDTH_D3', ('Natural', 24, '12 : 36')),
                  ('WIDTH_SYMBOL_D3', ('Natural', 12)),
                  ('USE_PACKETS_D3', ('Boolean', True)),
                  ('USE_EMPTY_D3', ('Boolean', True)),
                  ('D4_USE_CHANNEL', ('Boolean', True)),
                  ('D4_MAX_CHANNEL', ('Natural', 3)),
                  ('WIDTH_DATA', ('Natural', 12)),
                  ('SYMBOL_WIDTH_DATA', ('Natural', 3)),
                  ('USE_PACKETS_DATA', ('Boolean', True)),
                  ('USE_EMPTY_DATA', ('Boolean', True)),
                  ('DATA_USE_CHANNEL', ('Boolean', True)),
                  ('DATA_MAX_CHANNEL', ('Natural', 3)),
                  ('DATA_WIDTH_ERROR', ('Natural', 2)),
                  ('WIDTH_Q', ('Natural', 32)),
                  ('Q1_WIDTH_ERROR', ('Natural', 2)),
                  # a MM Slave can be a bit of work, although most values
                  # can be either defaults or plain integers
                  ('WIDTH_MM_D', ('Natural', 32)),
                  ('WIDTH_AS', ('Natural', 4)),
                  ('MAXIMUM_BURSTCOUNT', ('Natural', 4)),
                  ('WIDTH_BURSTCOUNT', ('Natural', 4)),
                  ('BURST_ON_BURST_BOUNDARIES_ONLY', ('Boolean', True)),
                  ('LINE_WRAP_BURSTS', ('Boolean', True)),
                  ('WRITE_WAIT_TIME', ('Natural', 1)),
                  ('MAXIMUM_PENDING_READ_TRANSACTIONS', ('Natural', 1)),
                  ('HOLD_TIME', ('Natural', 1)),
                  ('READ_WAIT_TIME', ('Natural', 1)),
                  ('READ_LATENCY', ('Natural', 1)),
                  ('BRIDGES_TO_MASTER', ('Boolean', False)),
                  ('SETUP_TIME', ('Natural', 0)),
                  ('WIDTH_AM', ('Natural', 7))
                  ),
                 # connection points
                 (('Clock', ('Clk', 0)),
                  ('Reset', ('Reset', 'Clk')),
                  # a minimal ST-sink
                  ('Sink', ('In0', ('Clk', 'Reset'),
                            ('D0', 'WIDTH_D', 'WIDTH_D'))),
                  # with forced Packet signals
                  ('Sink', ('In1', ('Clk', 'Reset'),
                            ('D1', 13), (True,))),
                  # and forced Empty signals
                  ('Sink', ('In2', ('Clk', 'Reset'),
                            ('D2', 'WIDTH_D', 3), (True, True))),
                  # with selectable Packet / Empty signals
                  ('Sink', ('In3', ('Clk', 'Reset'),
                            ('D3', 'WIDTH_D3', 'WIDTH_SYMBOL_D3'),
                            ('USE_PACKETS_D3', 'USE_EMPTY_D3'))),
                  # adding channel info
                  ('Sink', ('In4', ('Clk', 'Reset'),
                            ('D4', 'WIDTH_D'), None, (True, False),
                            ('D4_USE_CHANNEL', 'D4_MAX_CHANNEL'))),
                  # the full works
                  ('Sink', ('In5', ('Clk', 'Reset'),
                            ('Data', 'WIDTH_DATA', 'SYMBOL_WIDTH_DATA'),
                            ('USE_PACKETS_DATA', 'USE_EMPTY_DATA'),
                            ('DATA_USE_CHANNEL', 'DATA_MAX_CHANNEL'),
                            'DATA_WIDTH_ERROR')),
                  # no ready signal
                  ('Sink', ('In6', ('Clk', 'Reset'),
                            ('D6', 'WIDTH_D', 'WIDTH_D', 'NO_READY'))),
                  # no valid signal
                  ('Sink', ('In7', ('Clk', 'Reset'),
                            ('D7', 'WIDTH_D', 'WIDTH_D', 'NO_VALID'))),
                  # a 'static' one
                  ('Sink', ('In8', ('Clk', 'Reset'),
                            ('D8', '16', '8'), (True, True),)),
                  ('Clock', ('ClkOut', 0)),
                  ('Reset', ('ResetOut', 'ClkOut', 'None')),
                  # alternate form of defining symbolwidth == width
                  ('Source', ('Out0', ('ClkOut', 'ResetOut'), ('Q0', 'WIDTH_Q', None))),
                  # adding an errors output
                  ('Source', ('Out1', ('ClkOut', 'ResetOut'),
                              ('Q1', 'WIDTH_Q'), (True,), (None,), 'Q1_WIDTH_ERROR')),
                  # adding an errors output
                  # fixed error width and description
                  ('Source', ('Out2', ('ClkOut', 'ResetOut'),
                              ('Q2', '24', 12), (True, True), (True, 3), (2, ('one', 'two')))),
                  # a MemoryMapped Slave
                  ('Clock', ('ClkMMS', 0)),
                  ('Reset', ('ResetMMS', 'ClkMMS')),
                  # if WIDTH_BURSTCOUNT not given (or None) width is calculated
                  ('MMSlave', ('csr', ('CLkMMS', 'ResetMMS'),
                               ('AS', 'WIDTH_AS'),
                               ('BurstCountS', 'MAXIMUM_BURSTCOUNT', 'WIDTH_BURSTCOUNT',
                                'BURST_ON_BURST_BOUNDARIES_ONLY', 'LINE_WRAP_BURSTS'),
                               'WIDTH_MM_D',
                               ('WDS', 'WrS', 'WIDTH_MM_D', 'ByteEnableS', 'WRITE_WAIT_TIME', 'HOLD_TIME'),
                               ('RdS', 'RQS', 'MAXIMUM_PENDING_READ_TRANSACTIONS', 'READ_WAIT_TIME', 'READ_LATENCY'),
                               'WaitRequestS', 'ReadDataValidS', 'SETUP_TIME', 'BRIDGES_TO_MASTER',
                               )
                   ),
                  # a lot of parameters can be fixed integers ... or left-out
                  ('MMSlave', ('csr2', ('CLkMMS', 'ResetMMS'),
                               ('AS2', '4'),
                               None,
                               '32',
                               ('WDS2', 'WrS2',),
                               ('RdS2', 'RQS2',),
                               None, None, None, None,
                               )
                   ),
                  # a write-only slave
                  ('MMSlave', ('csr3', ('CLkMMS', 'ResetMMS'),
                               ('AS3', '4'),
                               None,
                               '32',
                               ('WDS3', 'WrS3',),
                               None,
                               None, None, None, None,
                               )
                   ),
                  # a read-only slave
                  ('MMSlave', ('csr4', ('CLkMMS', 'ResetMMS'),
                               ('AS4', '5'),
                               None,
                               '32',
                               None,
                               ('RQS4', 'RdS43',),
                               None, None, None, None,
                               )
                   ),
                  # a MemoryMapped Master looks 'almost' the same
                  # if WIDTH_BURSTCOUNT not given (or None) width is calculated
                  ('Clock', ('ClkMMM', 0)),
                  ('Reset', ('ResetMMM', 'ClkMMM')),
                  ('MMMaster', ('mmm', ('CLkMMM', 'ResetMMM'),
                                ('AM', 'WIDTH_AM'),
                                ('BurstCountM', 'MAXIMUM_BURSTCOUNT', 'WIDTH_BURSTCOUNT',
                                 'BURST_ON_BURST_BOUNDARIES_ONLY', 'LINE_WRAP_BURSTS'),
                                'WIDTH_MM_D',
                                ('WDM', 'WrM', 'WIDTH_MM_D', 'ByteEnableM', 'WRITE_WAIT_TIME', 'HOLD_TIME'),
                                ('RdM', 'RQM', 'MAXIMUM_PENDING_READ_TRANSACTIONS', 'READ_WAIT_TIME', 'READ_LATENCY'),
                                'WaitRequestM', 'ReadDataValidM', 'SETUP_TIME'
                                )
                   ),
                  ('Conduit', ('Sequence', ('ClkOut', 'ResetOut'), (('SequenceID', 'Input', 'WIDTH_SEQUENCE_ID'),
                                                                    ('Time', 'Input', '16'))))
                  ),
                 testbench=None,
                 convert=None,
                 gentcl=('1.0', 'Josy', 'C-Cam/Avalon')
                 )

        # for reference
        g.show()

    except qerror.QError as exc:
        print("Something went wrong! -> {}" .format(exc))
