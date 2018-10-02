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
import string
import collections

import myhdl

import Utilities.hdlutils as hdlutils

import Utilities.Qgen.qerror as qerror

# from Source.interfaces import AvalonInterface

indent = 0

BIG_ENDIAN = 1
LITTLE_ENDIAN = 2

# def keepline(line, keepsets):
#     for key, s, value in keepsets:
#         if s in line:
#             if key or value is None:
#                 return False, ''
#             else:
#                 return True, string.replace(line, s, str(value))
#     # no match, do not drop
#     return True, line


class ConnectionPoints(object):
    ''' base class for the connection points '''

    def __init__(self, genericslist=None, connectionpointlist=None):
        self.connectionpointslist = collections.OrderedDict()
        self.high = 0
        self.section = None
        self.genericslist = genericslist
        if connectionpointlist:
            for cp in connectionpointlist:
                #                  print( cp )
                self.addconnectionpoint(cp)

    def addconnectionpoint(self, cp):
        if cp[1][0] in self.connectionpointslist:
            raise qerror.QError(
                "Connection Point {} already in dictionary" .format(cp[1][0]))

        if cp[0] == 'Clock':
            value = Clock(self.genericslist, cp[1])
        elif cp[0] == 'Reset':
            value = Reset(self.genericslist, cp[1])
        elif cp[0] == 'ClockReset':
            self.addconnectionpoint(('Clock', cp[0]))
            self.addconnectionpoint(('Reset', (cp[0][0], cp[1][0], cp[1][1])))
        elif cp[0] == 'Sink':
            value = SinkSource('Sink', self.genericslist, cp[1])
        elif cp[0] == 'Source':
            value = SinkSource('Source', self.genericslist, cp[1])
        elif cp[0] == 'MMMaster':
            value = MMSlaveMaster('MMMaster', self.genericslist, cp[1])
        elif cp[0] == 'MMSlave':
            value = MMSlaveMaster('MMSlave', self.genericslist, cp[1])
        elif cp[0] == 'Conduit':
            value = Conduit('Conduit', self.genericslist, cp[1])
        else:
            raise ValueError("Unknown Connection Point {}".format(cp[0]))
        self.connectionpointslist.update({cp[1][0]: value})

    def addclock(self, name, frequency=0):
        if name in self.connectionpointslist:
            raise qerror.QError(
                "Connection Point {} already in dictionary" .format(name))
        self.connectionpointslist.update({name: Clock(self.genericslist, (name, frequency))})

    def addreset(self, name, associatedclock=None, edges=None):
        if name in self.connectionpointslist:
            raise qerror.QError(
                "Connection Point {} already in dictionary" .format(name))
        self.connectionpointslist.update({name: Reset(self.genericslist, (name, associatedclock, edges))})

    def addsinksource(self, sinkorsource, name, associatedclockreset, data,
                      packets=None, channel=None, error=None, ):
        ''' sinkorsourece:             'Sink' or 'Source'
             name:                       actual 'name' for the module
             associatedclockreset:     tuple( clock, reset)
                                           clock: 'name' of the associated clock
                                           reset: 'name' of the associated reset
             data:                       tuple( 'name', width, symbolwidth , omithandshake)
                                           'name': of Data signal, handshake signals will be derived by suffixing  'Valid' and 'Ready'
                                           width : 'name' in generic list of immediate value
                                                    bitwidth of the Data
                                           symbolwidth : optional, 'name' in generic list or immediate value
                                                    width of the symbols making up the Data
                                           omithandshake: choice between NO_READY and NO_VALID
             packets:                    tuple( usepackets, useempty )
                                           usepackets: 'name' in generic list or immediate value
                                                        packet signals will be derived by suffixing the 'Data' name with 'SoP' and 'EoP'
                                           useempty:    optional, defaults to False.
                                                        'name' in generic list or immediate value
                                                        adds empty signal (if symbolwidth is a multiple of width)
                                           signal name is derived by suffixing 'Data' name with 'Empty'
             channel:                    tuple( width, maxchannel )
                                           width: 'name' in generic list or immediate value
                                           maxchannel: optional,'name' in generic list or immediate value
                                           signal name is derived by suffixing 'Data' name with 'Channel'
             error:                     tuple( width, description )
                                           width: 'name' in generic list or immediate value
                                           description : optional, 'name' in generic list or immediate value
                                           signal name is derived by suffixing 'Data' name with 'Error'
        '''
        if name in self.connectionpointslist:
            raise qerror.QError(
                "Connection Point {} already in dictionary" .format(name))

        self.connectionpointslist.update({name: SinkSource(sinkorsource, self.genericslist, (name, associatedclockreset, data, packets, channel, error))})

    def addMMSlaveMaster(self, slaveormaster, name, associatedclockreset, address, burst=None, width=32,
                         writedesc=None, readdesc=None, waitrequest=None, readdatavalid=None, setuptime=None, bridgestomaster=None):
        ''' slaveormaster:             'MMSlave' or 'MMMaster'
             name:                       actual 'name' for the module
             associatedclockreset:     tuple( clock, reset)
                                           clock: 'name' of the associated clock
                                           reset: 'name' of the associated reset
             address:                    tuple( 'name', width )
                                           'name': of address signal
                                           width : 'name' in generic list of immediate value
                                                    bitwidth of the address signbal
             burst:                     tuple(name, 'MAXIMUM_BURSTCOUNT', 'WIDTH_BURSTCOUNT', 'BURST_ON_BURST_BOUNDARIES_ONLY', 'LINE_WRAP_BURSTS')
                                           'name': of burstcount signal
                                           maxburstcount: 'name' in generic list or immediate value
                                           width : 'name' in generic list or immediate value
             width:                     width of databus
             writedesc:                 tuple('WDS', 'WrS', 'SymbolWidth', 'ByteEnableS', 'WRITE_WAIT_TIME', 'HOLD_TIME'),
             readdesc:                  tuple('RdS', 'RQS', 'MAXIMUM_PENDING_READ_TRANSACTIONS', 'READ_WAIT_TIME', 'READ_LATENCY'),

        '''
        if name in self.connectionpointslist:
            raise qerror.QError(
                "Connection Point {} already in dictionary" .format(name))
        self.connectionpointslist.update({name: MMSlaveMaster(slaveormaster, self.genericslist,
                                                              (name, associatedclockreset, address,
                                                               burst, width, writedesc, readdesc,
                                                               waitrequest, readdatavalid, setuptime, bridgestomaster)
                                                              )})

    def addConduit(self, name, associatedclockreset, signals):
        if name in self.connectionpointslist:
            raise qerror.QError(
                "Connection Point {} already in dictionary" .format(name))
        self.connectionpointslist.update(
            {name: Conduit('Conduit', self.genericslist, (name, associatedclockreset, signals))})

    def makesignals(self, interface):
        return self.connectionpointslist[interface].makesignals()

#     def interfacesignals(self, interface):
#         return self.connectionpointslist[interface].interfacesignals()

    def show(self):
        global indent
        print('Connection Points')
        indent += 4
        for cp in self.connectionpointslist.values():
            cp.show()
        if indent > 4:
            indent -= 4
        else:
            indent = 0
        print()

    def widthempty(self, key):
        if key:
            if isinstance(key, str) and isinstance(self.connectionpointslist[key], SinkSource):
                return self.connectionpointslist[key].WIDTH_EMPTY
        # default answer
        return None

    def widthchannel(self, key):
        if key:
            if isinstance(key, str) and isinstance(self.connectionpointslist[key], SinkSource):
                return self.connectionpointslist[key].WIDTH_CHANNEL
        # default answer
        return None


class ConnectionPoint(object):
    '''
        base class to define a Qsys Connection Point
    '''

    def __init__(self):
        self.description = None

    def addconnectionpoint(self, tcltarget):
        # raise 'Unhandled ConnectionPoint \'{}\''.format(self.name)
        pass


class Clock(ConnectionPoint):

    def __init__(self, _, decl):
        ConnectionPoint.__init__(self)
        self.cptype = 'Clock'
        self.name = decl[0]
        if len(decl) > 1:
            self.rate = decl[1]
        else:
            self.rate = 0

    def show(self):
        global indent
        print('{:{width}}Connection Point {}: {} : {} Hz' .format(
            ' ', self.cptype, self.name, self.rate, width=indent))

    def tclconnectionpoint(self, tcltarget):
        for line in ['# +-----------------------------------\n',
                     '# | connection point _clk_\n',
                     '# |\n',
                     'add_interface _clk_ clock end\n',
                     'set_interface_property _clk_ clockRate _clockrate_\n',
                     'set_interface_property _clk_ ENABLED true\n',
                     'add_interface_port _clk_ _clk_ clk Input 1\n',
                     '# |\n',
                     '# +-----------------------------------\n\n']:
            line = string.replace(line, '_clk_', self.name)
            line = string.replace(line, '_clockrate_', '{}'.format(self.rate))
            tcltarget.write(line)

    def elaborate(self, tcltarget):
        pass


class Reset(ConnectionPoint):

    def __init__(self, _, decl):
        ConnectionPoint.__init__(self)
        self.cptype = 'Reset'
        self.name = decl[0]
        self.associatedclock = decl[1]
        self.synchronousedges = None
        if len(decl) > 2 and decl[2] is not None:
            self.synchronousedges = decl[2]

    def show(self):
        print('{:{width}}Connection Point {}: {}, associated clock: {}, edges: {}' .format(
            ' ', self.cptype, self.name, self.associatedclock, self.synchronousedges, width=indent))

    def tclconnectionpoint(self, tcltarget):
        for line in ['# +-----------------------------------\n',
                     '# | connection point _reset_\n',
                     '# |\n',
                     'add_interface _reset_ reset end\n',
                     'set_interface_property _reset_ associatedClock _clk_\n',
                     'set_interface_property _reset_ synchronousEdges _edges_\n',
                     'set_interface_property _reset_ ENABLED true\n',
                     'add_interface_port _reset_ _reset_ reset Input 1\n',
                     '# |\n',
                     '# +-----------------------------------\n\n']:
            line = string.replace(line, '_reset_', self.name)
            line = string.replace(line, '_clk_', self.associatedclock)
            line = string.replace(
                line, '_edges_', '{}'.format(self.synchronousedges))
            tcltarget.write(line)

    def elaborate(self, tcltarget):
        pass


class SinkSource(ConnectionPoint):

    def __init__(self, sinkorsource, genericslist, decl):
        ConnectionPoint.__init__(self)
        self.cptype = sinkorsource
        self.genericslist = genericslist

        # append 'None's to decl so we can unpack 'ruecksichtlos'
        ldecl = list(decl)
        for _ in range(6 - len(decl)):
            ldecl.append(None)

        self.name, (self.associatedclock,
                    self.associatedreset), decl_d, decl_pk, decl_ch, decl_er = ldecl
        self.readylatency = 0

        # mandatory
        if len(decl_d) > 3:
            d, w, s, decl_hs = decl_d[:4]

        elif len(decl_d) > 2:
            d, w, s = decl_d[:3]
            decl_hs = None
        else:
            d, w = decl_d[:2]
            s = None
            decl_hs = None

        # the name of the Data
        self.Data = d + 'PayLoad'
        # width
        self.key_WIDTH_D = None
        if isinstance(w, int):
            self.WIDTH_D = w
        elif isinstance(w, str):
            if w.isdigit():
                self.WIDTH_D = int(w)
            else:
                self.key_WIDTH_D = w
                self.WIDTH_D = genericslist.value(w)
        else:
            raise qerror.QError(
                '{} has invalid WIDTH_D: {}' .format(self.name, w))

        #  symbol width
        self.key_SYMBOL_WIDTH_D = None
        if s is None:
            self.SYMBOL_WIDTH_D = self.WIDTH_D
        elif isinstance(s, int):
            self.SYMBOL_WIDTH_D = s
        elif isinstance(s, str):
            if s[0].isdigit():
                self.SYMBOL_WIDTH_D = int(s)
            else:
                self.key_SYMBOL_WIDTH_D = s
                self.SYMBOL_WIDTH_D = genericslist.value(s)
        else:
            raise qerror.QError(
                '{} has invalid SYMBOL_WIDTH_D: {}' .format(self.name, decl[2][2]))
        self.symbolsperbeat = self.WIDTH_D / self.SYMBOL_WIDTH_D

        # optional

        # handshake signals
        self.valid = d + 'Valid'
        self.ready = d + 'Ready'
        self.key_HANDSHAKE = None
        if decl_hs:
            if isinstance(decl_hs, str):
                if decl_hs == 'NO_READY':
                    self.ready = None
                elif decl_hs == 'NO_VALID':
                    self.valid = None
                elif decl_hs == 'HANDSHAKE':
                    #                      self.ready = None
                    #                      self.valid = None
                    self.key_HANDSHAKE = 'HANDSHAKE'
                    hs = genericslist.value(self.key_HANDSHAKE)
                    if hs == 'Standard':
                        pass
                    elif hs == 'NO_READY':
                        self.ready = None
                    elif hs == 'NO_VALID':
                        self.valid = None
                    elif hs == 'NO_BACKPRESSURE':
                        pass
                    elif hs == 'NO_FEED':
                        pass

            else:
                raise qerror.QError(
                    " {}: Invalid Handshake Signals definition" .format(self.name))

        # set to default
        self.key_USE_PACKETS = None
        self.SoP = None
        self.EoP = None
        self.key_USE_EMPTY = None
        self.WIDTH_EMPTY = None
        self.empty = None
        self.key_USE_CHANNEL = None
        self.WIDTH_CHANNEL = None
        self.channel = None
        self.key_MAX_CHANNEL = None
        self.MAX_CHANNEL = None
        self.key_WIDTH_ERROR = None
        self.WIDTH_ERROR = None
        self.error = None

        # packets
        if decl_pk:
            if len(decl_pk) > 1:
                p, e = decl_pk
            else:
                if isinstance(decl_pk, tuple):
                    p = decl_pk[0]
                else:
                    p = decl_pk

                e = None

            self.key_USE_PACKETS = p
            self.key_USE_EMPTY = e
            if p is not None:
                if p or (isinstance(p, str) and genericslist.value(p)):
                    self.SoP = d + 'SoP'
                    self.EoP = d + 'EoP'
                    if e is not None:  # and genericslist.value(e):
                        if self.WIDTH_D > self.SYMBOL_WIDTH_D:
                            self.empty = d + 'Empty'
                            self.WIDTH_EMPTY = hdlutils.widthu(
                                self.WIDTH_D / self.SYMBOL_WIDTH_D)
                        else:
                            pass

                else:
                    raise qerror.QError(
                        '{} has invalid Packet description {}' .format(self.name, decl[3]))

        # channel
        if decl_ch:
            if len(decl_ch) > 1:
                c, m = decl_ch
            else:
                c = decl_ch[0]
                m = None

            if c:
                self.channel = d + 'Channel'
                self.key_USE_CHANNEL = c
                if isinstance(c, str) and isinstance(m, str):
                    if m is not None:
                        self.WIDTH_CHANNEL = hdlutils.widthu(
                            genericslist.value(m) + 1) if genericslist.value(m) > 1 else 1
                        self.key_MAX_CHANNEL = m
                        self.MAX_CHANNEL = genericslist.value(m)
                elif isinstance(m, int):
                    self.MAX_CHANNEL = m
                    if m > 1:
                        self.WIDTH_CHANNEL = hdlutils.widthu(m)
                    else:
                        self.WIDTH_CHANNEL = 1
                    self.key_MAX_CHANNEL = None
                else:
                    raise qerror.QError(
                        '{} has invalid Channel description {}' .format(self.name, decl[4]))

        # error
        self.key_WIDTH_ERROR = None
        self.WIDTH_ERROR = None
        self.EROR_DESCRIPTOR = None
        if decl_er:
            self.error = d + 'Error'
            if isinstance(decl_er, tuple):
                ew = decl_er[0]
                if isinstance(ew, int):
                    # fixed width
                    self.WIDTH_ERROR = ew
                elif isinstance(ew, str):
                    self.key_WIDTH_ERROR = decl_er
                    self.WIDTH_ERROR = genericslist.value(decl_er)
                else:
                    print(
                        'Undefined tuple {} for {}!'.format(decl_er, self.error))
                if len(decl_er) > 1 and isinstance(decl_er[1], tuple):
                    # have a errordescriptor list
                    self.EROR_DESCRIPTOR = decl_er[1]

            elif isinstance(decl_er, int):
                self.WIDTH_ERROR = decl_er
                # no descriptor list
            elif isinstance(decl_er, str):
                self.key_WIDTH_ERROR = decl_er
                self.WIDTH_ERROR = genericslist.value(decl_er)
            else:
                print('Undefined width for {}!'.format(self.error))

#     def interfacesignals(self):
#         # make an empty ST interface (effectively empty)
#         r = AvalonInterface.ST()
#         # add one for one
#         if self.Data:
#             r.Data = myhdl.Signal(myhdl.intbv(0)[self.WIDTH_D:])
#
#         if self.SoP:
#             r.SoP = myhdl.Signal(bool(0))
#             r.EoP = myhdl.Signal(bool(0))
#             if self.WIDTH_EMPTY:
#                 r.Empty = myhdl.Signal(myhdl.intbv(0)[self.WIDTH_EMPTY])
#
#         if self.WIDTH_CHANNEL:
#             r.Channel = myhdl.Signal(myhdl.intbv(0)[self.WIDTH_CHANNEL])
#
#         if self.WIDTH_ERROR:
#             r.Error = myhdl.Signal(myhdl.intbv(0)[self.WIDTH_ERROR:])
#
#         if self.valid:
#             r.Valid = myhdl.Signal(bool(0))
#
#         if self.ready:
#             r.Ready = myhdl.Signal(bool(0))
#
#         return r

    def makesignals(self):
        # add one for one
        data = None
        sop = None
        eop = None
        empty = None
        channel = None
        error = None
        valid = None
        ready = None
        if self.Data:
            data = myhdl.Signal(myhdl.intbv(0)[self.WIDTH_D:])

        if self.SoP:
            sop = myhdl.Signal(bool(0))
            eop = myhdl.Signal(bool(0))
            if self.WIDTH_EMPTY:
                empty = myhdl.Signal(myhdl.intbv(0)[self.WIDTH_EMPTY])

        if self.WIDTH_CHANNEL:
            channel = myhdl.Signal(myhdl.intbv(0)[self.WIDTH_CHANNEL])

        if self.WIDTH_ERROR:
            #             print( self.WIDTH_ERROR )
            error = myhdl.Signal(myhdl.intbv(0)[self.WIDTH_ERROR:])

        if self.valid:
            valid = myhdl.Signal(bool(0))

        if self.ready:
            ready = myhdl.Signal(bool(0))

        # only return the necessary ones, or all?
        return data, sop, eop, empty, channel, error, valid, ready

    def show(self):
        global indent
        print('{: >{width}}Connection Point {}: {}' .format(
            '', self.cptype, self.name, width=indent))
        indent += 4
        print('{: >{width}}associated clock and reset: {}, {}' .format(
            '', self.associatedclock, self.associatedreset, width=indent))
        print('{: >{width}}Data: \'{}\' WIDTH_D: {}, WIDTH_SYMBOL: {}, SymbolsPerBeat: {}'
              .format(' ', self.Data, self.WIDTH_D, self.SYMBOL_WIDTH_D, self.symbolsperbeat, width=indent))
        print('{: >{width}}Handshake Signals: {}, {}' .format(
            '', self.ready, self.valid, width=indent))
        if self.key_USE_PACKETS:
            print('{: >{width}}Packet Signals: {}, {}' .format(
                '', self.SoP, self.EoP, width=indent))
            if self.key_USE_EMPTY:
                print('{: >{width}}Empty: {} WIDTH_EMPTY: {}' .format(
                    '', self.empty, self.WIDTH_EMPTY, width=indent))
        if self.key_USE_CHANNEL:
            print('{: >{width}}Channel: {} WIDTH_CHANNEL: {}, MAX_CHANNEL{}' .format(
                '', self.channel, self.WIDTH_CHANNEL, self.MAX_CHANNEL, width=indent))
        if self.key_WIDTH_ERROR:
            print('{: >{width}}Error: {} WIDTH_ERROR: {}' .format(
                '', self.error, self.WIDTH_ERROR, width=indent))

        indent -= 4

    def tclconnectionpoint(self, tcltarget):

        tcltarget.write(
            '# +-----------------------------------\n# | connection point {}\n# |\n' .format(self.name))
        tcltarget.write('add_interface {} avalon_streaming {}\n' .format(
            self.name, 'end' if self.cptype == 'Sink' else 'start'))
        tcltarget.write('set_interface_property {} associatedClock {}\n' .format(
            self.name, self.associatedclock))
        tcltarget.write('set_interface_property {} associatedReset {}\n' .format(
            self.name, self.associatedreset))
        if True:
            tcltarget.write(
                'set_interface_property {} firstSymbolInHighOrderBits true\n' .format(self.name))

        tcltarget.write('set_interface_property {} readyLatency {}\n' .format(
            self.name, self.readylatency))
        tcltarget.write(
            'set_interface_property {} ENABLED true\n' .format(self.name))

        if self.key_HANDSHAKE is None:
            if self.valid:
                tcltarget.write('add_interface_port {} {} valid {} 1\n' .format(
                    self.name, self.valid, 'Input' if self.cptype == 'Sink' else 'Output'))

            if self.ready:
                tcltarget.write('add_interface_port {} {} ready {} 1\n' .format(
                    self.name, self.ready, 'Input' if self.cptype == 'Source' else 'Output'))

        if self.key_WIDTH_D is None and self.key_SYMBOL_WIDTH_D is None:
            tcltarget.write('add_interface_port {} {} data {} {}\n' .format(
                self.name, self.Data, 'Input' if self.cptype == 'Sink' else 'Output', self.WIDTH_D))
            tcltarget.write('set_interface_property {} symbolsPerBeat {}\n' .format(
                self.name, self.symbolsperbeat))
            tcltarget.write('set_interface_property {} dataBitsPerSymbol {}\n' .format(
                self.name, self.SYMBOL_WIDTH_D))

        if self.key_USE_PACKETS is True:
            tcltarget.write('add_interface_port {} {} startofpacket {} 1\n' .format(
                self.name, self.SoP, 'Input' if self.cptype == 'Sink' else 'Output'))
            tcltarget.write('add_interface_port {} {} endofpacket {} 1\n' .format(
                self.name, self.EoP, 'Input' if self.cptype == 'Sink' else 'Output'))
            if self.key_USE_EMPTY is True:
                tcltarget.write('add_interface_port {} {} empty {} {}\n'
                                .format(self.name, self.empty, 'Input' if self.cptype == 'Sink' else 'Output', self.WIDTH_EMPTY))

        if self.key_MAX_CHANNEL is None and self.WIDTH_CHANNEL:
            tcltarget.write('add_interface_port {} {} channel {} {}\n' .format(
                self.name, self.channel, 'Input' if self.cptype == 'Sink' else 'Output', self.WIDTH_CHANNEL))

        if self.key_WIDTH_ERROR is None and self.WIDTH_ERROR:
            tcltarget.write('add_interface_port {} {} error {} {}\n' .format(
                self.name, self.error, 'Input' if self.cptype == 'Sink' else 'Output', self.WIDTH_ERROR))
            if self.EROR_DESCRIPTOR:
                # unpack the tuple e,genericslist, ('one', 'two', 'three') into "one two
                # three" -> 'join to the rescue!
                tcltarget.write('set_interface_property {} errorDescriptor \"{}\"\n' .format(
                    self.name, " ".join(self.EROR_DESCRIPTOR)))

        tcltarget.write('# |\n# +-----------------------------------\n\n')

    def elaborate(self, tcltarget):
        tcltarget.write('\t#--- {} {}\n'
                        .format(self.cptype, self.name))
        if self.key_WIDTH_D:
            # find out if this a derived parameter, in which case the
            # 'elaborate' call has computed the value
            if self.genericslist.isderived(self.key_WIDTH_D):
                tcltarget.write('\tset {0}_d_width [ lindex $l [expr [lsearch $l "{1}"] +1]]\n'
                                .format(self.name, self.key_WIDTH_D))
                tcltarget.write('\tset_parameter_value {1} ${0}_d_width \n'
                                .format(self.name, self.key_WIDTH_D))
                # mark that the derived key has been used
                self.genericslist.markderived(self.key_WIDTH_D)
            else:
                tcltarget.write('\tset {}_d_width [ get_parameter_value {} ]\n'
                                .format(self.name, self.key_WIDTH_D))

            tcltarget.write('\tadd_interface_port {0} {1} data {2} ${0}_d_width\n'
                            .format(self.name, self.Data, 'Input' if self.cptype == 'Sink' else 'Output'))
            if self.key_SYMBOL_WIDTH_D:
                tcltarget.write('\tset {}_d_symbol_width [ get_parameter_value {} ]\n'
                                .format(self.name, self.key_SYMBOL_WIDTH_D))
                tcltarget.write('\tset_interface_property {0} dataBitsPerSymbol ${0}_d_symbol_width\n'
                                .format(self.name))
                tcltarget.write(
                    '\tset_interface_property {0} symbolsPerBeat [expr ${0}_d_width / ${0}_d_symbol_width]\n' .format(self.name))

            else:
                tcltarget.write(
                    '\tset_interface_property {} symbolsPerBeat 1\n' .format(self.name))
                tcltarget.write('\tset_interface_property {0} dataBitsPerSymbol ${0}_d_width \n'
                                .format(self.name))
        if self.key_HANDSHAKE:
            tcltarget.write('\tset hs [ get_parameter_value HANDSHAKE ]\n')
            tcltarget.write('\tif {$hs == "Standard"} {\n')
            tcltarget.write('\t\tadd_interface_port {0} {1} valid {2} 1 \n'.format(
                self.name, self.valid, 'Input' if self.cptype == 'Sink' else 'Output'))
            tcltarget.write('\t\tadd_interface_port {0} {1} ready {2} 1 \n'.format(
                self.name, self.ready, 'Input' if self.cptype == 'Source' else 'Output'))
            tcltarget.write('\t} elseif {$hs == "NO_READY"} {\n')
            tcltarget.write('\t\tadd_interface_port {0} {1} valid {2} 1 \n'.format(
                self.name, self.valid, 'Input' if self.cptype == 'Sink' else 'Output'))
            tcltarget.write('\t} elseif {$hs == "NO_VALID"} {\n')
            tcltarget.write('\t\tadd_interface_port {0} {1} ready {2} 1 \n'.format(
                self.name, self.ready, 'Input' if self.cptype == 'Source' else 'Output'))
            tcltarget.write('\t} elseif {$hs == "NO_BACKPRESSURE"} {\n')
            tcltarget.write('\t\tadd_interface_port {0} {1} valid {2} 1 \n'.format(
                self.name, self.valid, 'Input' if self.cptype == 'Sink' else 'Output'))
            tcltarget.write('\t\tadd_interface_port {0} {1} ready {2} 1 \n'.format(
                self.name, self.ready, 'Input' if self.cptype == 'Source' else 'Output'))
            tcltarget.write(
                '\t\t set_port_property {} termination true\n'.format(self.ready))
            tcltarget.write('\t} elseif {$hs == "NO_FEED"} {\n')
            tcltarget.write('\t\tadd_interface_port {0} {1} valid {2} 1 \n'.format(
                self.name, self.valid, 'Input' if self.cptype == 'Sink' else 'Output'))
            tcltarget.write('\t\tadd_interface_port {0} {1} ready {2} 1 \n'.format(
                self.name, self.ready, 'Input' if self.cptype == 'Source' else 'Output'))
            tcltarget.write(
                '\t\t set_port_property {} termination true\n'.format(self.valid))
            tcltarget.write('\t}\n')

        if isinstance(self.key_USE_PACKETS, str):
            tcltarget.write('\tset {}_usepackets [ get_parameter_value {} ]\n'
                            .format(self.name, self.key_USE_PACKETS))
            tcltarget.write('\tif {{${}_usepackets}} {{\n'
                            .format(self.name))
            tcltarget.write('\t\tadd_interface_port {0} {1} startofpacket {3} 1\n\t\tadd_interface_port {0} {2} endofpacket {3} 1\n'
                            .format(self.name, self.SoP, self.EoP, 'Input' if self.cptype == 'Sink' else 'Output'))
            if self.key_USE_EMPTY is not None:
                if self.key_SYMBOL_WIDTH_D:
                    tcltarget.write('\t\tset_parameter_property {} ENABLED true\n'
                                    .format(self.key_USE_EMPTY))
                    tcltarget.write('\t\tset {0}_useempty [ get_parameter_value {1} ]\n'
                                    .format(self.name, self.key_USE_EMPTY))
                    tcltarget.write('\t\tif {{${0}_useempty }} {{\n'
                                    .format(self.name))
                    tcltarget.write('\t\t\tadd_interface_port {0} {1} empty {2} {3}\n'
                                    .format(self.name, self.empty, 'Input' if self.cptype == 'Sink' else 'Output', self.WIDTH_EMPTY))
                    tcltarget.write('\t\t}\n')
                tcltarget.write('\t} else {\n')
                tcltarget.write('\t\tset_parameter_property {} ENABLED false\n'
                                .format(self.key_USE_EMPTY))
            tcltarget.write('\t}\n')

        if self.key_USE_CHANNEL:
            tcltarget.write('\tset {0}_use_channel [ get_parameter_value {1} ]\n' .format(
                self.name, self.key_USE_CHANNEL))
            tcltarget.write('\tif {{${0}_use_channel}} {{\n'.format(self.name))
            tcltarget.write(
                '\t\tset_parameter_property {0} ENABLED true\n'.format(self.key_MAX_CHANNEL))
            tcltarget.write('\t\tset {0}_channel_max [get_parameter_value {1} ]\n' .format(
                self.name, self.key_MAX_CHANNEL))
            tcltarget.write('\t\t\tadd_interface_port {0} {1} channel {2} [log2ceiling ${0}_channel_max]\n'
                            .format(self.name, self.channel, 'Input' if self.cptype == 'Sink' else 'Output'))
            tcltarget.write('\t} else {\n')
            tcltarget.write(
                '\t\tset_parameter_property {} ENABLED false\n'.format(self.key_MAX_CHANNEL))
            tcltarget.write('\t}\n')

        if self.key_WIDTH_ERROR:
            # find out if this a derived parameter, in which case the
            # 'elaborate' call has computed the value
            if self.genericslist.isderived(self.key_WIDTH_ERROR):
                tcltarget.write('\tset {0}_error_width [ lindex $l [expr [lsearch $l "{1}"] +1]]\n'
                                .format(self.name, self.key_WIDTH_ERROR))
                tcltarget.write('\tset_parameter_value {1} ${0}_error_width \n'
                                .format(self.name, self.key_WIDTH_ERROR))
                # mark that the derived key has been used
                self.genericslist.markderived(self.key_WIDTH_ERROR)
            else:
                tcltarget.write('\tset {}_error_width [ get_parameter_value {} ]\n'
                                .format(self.name, self.key_WIDTH_ERROR))

            tcltarget.write(
                '\tif {{${0}_error_width > 0}} {{\n'.format(self.name))
            tcltarget.write('\t\tadd_interface_port {0} {1} error {2} ${0}_error_width\n\t}}\n'
                            .format(self.name, self.error, 'Input' if self.cptype == 'Sink' else 'Output'))


class MMSlaveMaster(ConnectionPoint):

    def __init__(self, slaveormaster, genericslist, decl):
        ConnectionPoint.__init__(self)
        self.cptype = slaveormaster
        self.genericslist = genericslist

        # un-pack decl
        self.name, decl_cr, decl_a, decl_bc, decl_width, decl_write, decl_read, self.waitrequest, self.readdatavalid, decl_sut = decl[
            :10]

        # associated clock and reset
        self.associatedclock, self.associatedreset = decl_cr

        # ('AS', 'WIDTH_AS'),
        # the slave is at least a one-word-only type
        self.address = None
        self.key_WIDTH_A = None
        self.WIDTH_A = 0
        if decl_a:
            # have an address tuple
            a, w = decl_a
            self.address = a
            if isinstance(w, str) and not w.isdigit():
                self.key_WIDTH_A = w
                self.WIDTH_A = genericslist.value(w)
            else:
                if isinstance(w, (int, long)):
                    self.WIDTH_A = w

                elif w.isdigit():
                    self.WIDTH_A = int(w)
                else:
                    raise qerror.QError("can't handle {} " .format(w))

        # ('BurstCountS', 'MAXIMUM_BURSTCOUNT_S', 'WIDTH_BURSTCOUNT_S', 'BURST_ON_BURST_BOUNDARIES_ONLY','LINE_WRAP_BURSTS_S'), # if WIDTH_BURSTCOUNT_S not given (or None) width is calculated
        self.burstcount = None
        self.WIDTH_BURSTCOUNT = None
        self.MAXIMUM_BURSTCOUNT = None
        self.key_MAXIMUM_BURSTCOUNT = None
        self.key_WIDTH_BURSTCOUNT = None
        self.WIDTH_BURSTCOUNT = None
        self.BURST_ON_BURST_BOUNDARIES_ONLY = False
        self.key_BURST_ON_BURST_BOUNDARIES_ONLY = None
        self.key_LINE_WRAP_BURSTS = None
        self.LINE_WRAP_BURSTS = False
        if decl_bc:
            self.burstcount, mbc = decl_bc[:2]
            if isinstance(mbc, str) and not mbc.isdigit():
                self.key_MAXIMUM_BURSTCOUNT = mbc
                self.MAXIMUM_BURSTCOUNT = genericslist.value(mbc)
            else:
                self.MAXIMUM_BURSTCOUNT = mbc
            self.WIDTH_BURSTCOUNT = hdlutils.widthr(self.MAXIMUM_BURSTCOUNT)

            if len(decl_bc) > 2:
                if decl_bc[2]:
                    if isinstance(decl_bc[2], str):
                        self.key_WIDTH_BURSTCOUNT = decl_bc[2]
                        self.WIDTH_BURSTCOUNT = genericslist.value(decl_bc[2])
                    else:
                        self.MAXIMUM_BURSTCOUNT = decl_bc[2]

            if len(decl_bc) > 3:
                if decl_bc[3]:
                    if isinstance(decl_bc[3], str):
                        self.key_BURST_ON_BURST_BOUNDARIES_ONLY = decl_bc[3]
                        self.BURST_ON_BURST_BOUNDARIES_ONLY = genericslist.value(
                            decl_bc[3])
                    else:
                        self.BURST_ON_BURST_BOUNDARIES_ONLY = decl_bc[3]

            if len(decl_bc) > 4:
                if decl_bc[4]:
                    if isinstance(decl_bc[4], str):
                        self.key_LINE_WRAP_BURSTS = decl_bc[4]
                        self.LINE_WRAP_BURSTS = genericslist.value(decl_bc[4])
                    else:
                        self.LINE_WRAP_BURSTS = decl_bc[4]

        self.key_WIDTH_MM_D = None
        self.WIDTH_MM_D = 32
        if decl_width:
            if isinstance(decl_width, str) and not decl_width.isdigit():
                self.key_WIDTH_MM_D = decl_width
                self.WIDTH_MM_D = genericslist.value(decl_width)
            else:
                if isinstance(decl_width, (int, long)):
                    self.WIDTH_MM_D = decl_width
                elif decl_width.isdigit():
                    self.WIDTH_MM_D = int(decl_width)
                else:
                    raise qerror.QError("can't handle {} " .format(decl_width))

        self.writedata = None
        self.wr = None
        self.byteenables = None
        self.WIDTH_BYTE_ENABLE = None
        self.key_WRITE_WAIT_TIME = None
        self.WRITE_WAIT_TIME = 0
        self.key_HOLD_TIME = None
        self.HOLD_TIME = 0
        self.key_SYMBOL_WIDTH = None
        self.SYMBOL_WIDTH = 8
        if decl_write:
            # the write Data section can be complicated
            self.writedata = decl_write[0]
            self.wr = decl_write[1]

            if len(decl_write) > 2:
                sw = decl_write[2]
                if isinstance(sw, str) and not sw.isdigit():
                    self.key_SYMBOL_WIDTH = sw
                    self.SYMBOL_WIDTH = genericslist.value(sw)
                else:
                    if isinstance(sw, str):
                        self.SYMBOL_WIDTH = int(sw)
                    else:
                        self.SYMBOL_WIDTH = sw

            if len(decl_write) > 3:
                if decl_write[3]:
                    self.byteenables = decl_write[3]
                    self.WIDTH_BYTE_ENABLE = self.WIDTH_MM_D / \
                        self.SYMBOL_WIDTH

            if len(decl_write) > 4:
                wwt = decl_write[4]
                if isinstance(wwt, str) and not wwt.isdigit():
                    self.key_WRITE_WAIT_TIME = wwt
                    self.WRITE_WAIT_TIME = genericslist.value(wwt)
                else:
                    if isinstance(wwt, str):
                        self.WRITE_WAIT_TIME = int(wwt)
                    else:
                        self.WRITE_WAIT_TIME = wwt

            if len(decl_write) > 5:
                ht = decl_write[5]
                if isinstance(ht, str) and not ht.isdigit():
                    self.key_HOLD_TIME = ht
                    self.HOLD_TIME = genericslist.value(ht)
                else:
                    if isinstance(ht, str):
                        self.HOLD_TIME = int(ht)
                    else:
                        self.HOLD_TIME = ht

        self.rd = None
        self.readdata = None
        self.MAXIMUM_PENDING_READ_TRANSACTIONS = 0
        self.key_MAXIMUM_PENDING_READ_TRANSACTIONS = None
        self.READ_WAIT_TIME = 1  # default ...
        self.key_READ_WAIT_TIME = None
        self.READ_LATENCY = 0
        self.key_READ_LATENCY = None
        if decl_read:
            # the write Data section can be complicated
            self.rd = decl_read[0]
            self.readdata = decl_read[1]
            if len(decl_read) > 2:
                if isinstance(decl_read[2], str):
                    self.key_MAXIMUM_PENDING_READ_TRANSACTIONS = decl_read[2]
                    self.MAXIMUM_PENDING_READ_TRANSACTIONS = genericslist.value(
                        decl_read[2])
                else:
                    self.MAXIMUM_PENDING_READ_TRANSACTIONS = decl_read[2]

            if len(decl_read) > 3:
                if isinstance(decl_bc[3], str):
                    self.key_READ_WAIT_TIME = decl_read[3]
                    self.READ_WAIT_TIME = genericslist.value(decl_read[3])
                else:
                    self.READ_WAIT_TIME = decl_read[3]
            if len(decl_read) > 4:
                if isinstance(decl_read[4], str):
                    self.key_READ_LATENCY = decl_read[4]
                    self.READ_LATENCY = genericslist.value(decl_read[4])
                else:
                    self.READ_LATENCY = decl_read[4]
        # 'WaitRequestS', 'ReadDataValidS', 'BRIDGES_TO_MASTER_S' , 'SETUP_TIME_S'

        self.key_SETUP_TIME = None
        self.SETUP_TIME = 0
        if isinstance(decl_sut, str):
            self.key_SETUP_TIME = decl_sut
            self.SETUP_TIME = genericslist.value(decl_sut)
        else:
            self.SETUP_TIME = decl_sut

        self.key_BRIDGES_TO_MASTER = None
        self.BRIDGES_TO_MASTER = 0
        if len(decl) > 10:
            decl_btm = decl[10]
            if decl_btm:
                if isinstance(decl_btm, str):
                    self.key_BRIDGES_TO_MASTER = decl_btm

#     def interfacesignals(self):
#         # make an empty MM interface (effectively empty)
#         r = AvalonInterface.MM()
#         if self.WIDTH_A:
#             r.A = myhdl.Signal(myhdl.intbv(0)[self.WIDTH_A:])
#
#         if self.wr:
#             r.Wr = myhdl.Signal(bool(0))
#             r.WD = myhdl.Signal(myhdl.intbv(0)[self.WIDTH_MM_D:])
#
#         if self.rd:
#             r.Rd = myhdl.Signal(bool(0))
#
#         if self.readdata:
#             r.RQ = myhdl.Signal(myhdl.intbv(0)[self.WIDTH_MM_D:])
#
#         if self.waitrequest:
#             r.WaitRequest = myhdl.Signal(bool(0))
#
#         if self.readdatavalid:
#             r.ReadDataValid = myhdl.Signal(bool(0))
#
#         if self.burstcount:
#             r.BurstCount = myhdl.Signal(myhdl.intbv(0)[self.WIDTH_BURSTCOUNT:])
#
#         if self.byteenables:
#             r.ByteEnables = myhdl.Signal(
#                 myhdl.intbv(0)[self.WIDTH_BYTE_ENABLE:])
#
#         return r

    def makesignals(self):
        A = None
        WD = None
        Wr = None
        Rd = None
        RQ = None
        WaitRequest = None
        ReadDataValid = None
        BurstCount = None
        ByteEnables = None

        if self.WIDTH_A:
            A = myhdl.Signal(myhdl.intbv(0)[self.WIDTH_A:])

        if self.wr:
            Wr = myhdl.Signal(bool(0))
            WD = myhdl.Signal(myhdl.intbv(0)[self.WIDTH_MM_D:])

        if self.rd:
            Rd = myhdl.Signal(bool(0))

        if self.readdata:
            RQ = myhdl.Signal(myhdl.intbv(0)[self.WIDTH_MM_D:])

        if self.waitrequest:
            WaitRequest = myhdl.Signal(bool(0))

        if self.readdatavalid:
            ReadDataValid = myhdl.Signal(bool(0))

        if self.burstcount:
            BurstCount = myhdl.Signal(myhdl.intbv(0)[self.WIDTH_BURSTCOUNT:])

        if self.byteenables:
            ByteEnables = myhdl.Signal(myhdl.intbv(0)[self.WIDTH_BYTE_ENABLE:])

        return A, WD, Wr, Rd, RQ, WaitRequest, ReadDataValid, BurstCount, ByteEnables

    def show(self):
        global indent
        print('{:{width}}Connection Point {}: {}' .format(
            ' ', self.cptype, self.name, width=indent))
        indent += 4
        print('{:{width}}associated clock and reset: {}, {}' .format(
            ' ', self.associatedclock, self.associatedreset, width=indent))
        if self.address:
            print('{:{width}}Address: {}, width: {}' .format(
                ' ', self.address, self.WIDTH_A, width=indent))
        if self.burstcount:
            print('{:{width}}BurstCount: {}, max: {}, width: {}, BurstOnBoaundaries: {}, LineWrapBursts: {}'
                  .format(' ', self.burstcount, self.MAXIMUM_BURSTCOUNT, self.WIDTH_BURSTCOUNT, self.BURST_ON_BURST_BOUNDARIES_ONLY, self.LINE_WRAP_BURSTS, width=indent))
        print('{:{width}}Width of DataBus: {}' .format(
            ' ', self.WIDTH_MM_D, width=indent))
        if self.writedata:
            print('{:{width}}WriteData: {}, Byte Enables: {}' .format(
                ' ', self.writedata, self.byteenables, width=indent))
        if self.readdata:
            print('{:{width}}ReadData: {}, Maximum Pending Read Transactions: {}, Read Wait Time: {}, Read Latency:{}'
                  .format(' ', self.readdata, self.MAXIMUM_PENDING_READ_TRANSACTIONS, self.READ_WAIT_TIME, self.READ_LATENCY, width=indent))
        if self.waitrequest:
            print('{:{width}}WaitRequest: {}' .format(
                ' ', self.waitrequest, width=indent))
        if self.readdatavalid:
            print('{:{width}}ReadDataValid: {}' .format(
                ' ', self.readdatavalid, width=indent))
        if self.SETUP_TIME:
            print('{:{width}}SetupTime: {}' .format(
                ' ', self.SETUP_TIME, width=indent))
        if self.BRIDGES_TO_MASTER:
            print('{:{width}}BridgesToMaster: {}' .format(
                ' ', self.BRIDGES_TO_MASTER, width=indent))
        indent -= 4

    def tclconnectionpoint(self, tcltarget):

        tcltarget.write('# +-----------------------------------\n')
        tcltarget.write('# |connection point {}\n'
                        .format(self.name))
        tcltarget.write('# |\n')
        tcltarget.write('add_interface {} avalon {}\n'
                        .format(self.name, 'start' if self.cptype == 'MMMaster'else 'end'))

        # verbatim
        tcltarget.write(
            'set_interface_property {} ENABLED true\n'.format(self.name))
        tcltarget.write(
            'set_interface_property {} addressUnits WORDS\n'.format(self.name))
        tcltarget.write(
            'set_interface_property {} timingUnits Cycles\n'.format(self.name))

        if self.key_BURST_ON_BURST_BOUNDARIES_ONLY is None:
            tcltarget.write('set_interface_property {} burstOnBurstBoundariesOnly {}\n'
                            .format(self.name, self.BURST_ON_BURST_BOUNDARIES_ONLY))

        if self.key_HOLD_TIME is None:
            tcltarget.write('set_interface_property {} holdTime {}\n'
                            .format(self.name, self.HOLD_TIME))

        if self.key_LINE_WRAP_BURSTS is None:
            tcltarget.write('set_interface_property {} linewrapBursts {}\n'
                            .format(self.name, self.LINE_WRAP_BURSTS))

        if self.readdata:
            if self.key_MAXIMUM_PENDING_READ_TRANSACTIONS is None:
                tcltarget.write('set_interface_property {} maximumPendingReadTransactions {}\n'
                                .format(self.name, self.MAXIMUM_PENDING_READ_TRANSACTIONS))

            if self.key_READ_LATENCY is None:
                tcltarget.write('set_interface_property {} readLatency {}\n'
                                .format(self.name, self.READ_LATENCY))

            if self.key_READ_WAIT_TIME is None:
                tcltarget.write('set_interface_property {} readWaitTime {}\n'
                                .format(self.name, self.READ_WAIT_TIME))

        if self.key_SETUP_TIME is None:
            tcltarget.write('set_interface_property {} setupTime {}\n'
                            .format(self.name, self.SETUP_TIME))

        if self.writedata:
            if self.key_WRITE_WAIT_TIME is None:
                tcltarget.write('set_interface_property {} writeWaitTime {}\n'
                                .format(self.name, self.WRITE_WAIT_TIME))

        if self.key_BRIDGES_TO_MASTER is None and self.cptype == 'MMSlave':
            tcltarget.write('set_interface_property {} bridgesToMaster {}\n'
                            .format(self.name, self.BRIDGES_TO_MASTER))

        tcltarget.write('set_interface_property {} bitsPerSymbol {} \n'.format(
            self.name, self.SYMBOL_WIDTH))

        tcltarget.write('set_interface_property {} associatedClock {}\n'.format(
            self.name, self.associatedclock))
        tcltarget.write('set_interface_property {} associatedReset {}\n'.format(
            self.name, self.associatedreset))

        if self.key_WIDTH_A is None:
            tcltarget.write('add_interface_port {} {} address {} {}\n'
                            .format(self.name, self.address, 'Input' if self.cptype == 'MMSlave' else 'Output', self.WIDTH_A))

        if self.wr:
            tcltarget.write('add_interface_port {} {} write {} 1\n'
                            .format(self.name, self.wr, 'Input' if self.cptype == 'MMSlave' else 'Output'))
            if self.key_WIDTH_MM_D is None:
                tcltarget.write('add_interface_port {} {} writedata {} {}\n'
                                .format(self.name, self.writedata, 'Input' if self.cptype == 'MMSlave' else 'Output', self.WIDTH_MM_D))

        if self.rd:
            tcltarget.write('add_interface_port {} {} read {} 1\n'
                            .format(self.name, self.rd, 'Input' if self.cptype == 'MMSlave' else 'Output'))
            if self.key_WIDTH_MM_D is None:
                tcltarget.write('add_interface_port {} {} readdata {} {}\n'
                                .format(self.name, self.readdata, 'Output' if self.cptype == 'MMSlave' else 'Input', self.WIDTH_MM_D))
        if self.waitrequest:
            tcltarget.write('add_interface_port {} {} waitrequest  {} 1\n'
                            .format(self.name, self.waitrequest, 'Input' if self.cptype == 'MMMaster' else 'Output'))

        if self.readdatavalid:
            tcltarget.write('add_interface_port {} {} readdatavalid  {} 1\n'
                            .format(self.name, self.readdatavalid, 'Input' if self.cptype == 'MMMaster' else 'Output'))

        if self.burstcount and self.key_WIDTH_BURSTCOUNT is None:
            tcltarget.write('add_interface_port {} {} burstcount {} {}\n'
                            .format(self.name, self.burstcount, 'Input' if self.cptype == 'MMSlave' else 'Output', self.WIDTH_BURSTCOUNT))

        if self.byteenables and self.key_WIDTH_MM_D is None:
            tcltarget.write('add_interface_port {} {} byteenable {} {}\n'
                            .format(self.name, self.byteenables, 'Input' if self.cptype == 'MMSlave' else 'Output', self.WIDTH_BYTE_ENABLE))

        tcltarget.write('# |\n' +
                        '# |\n' +
                        '# +-----------------------------------\n\n')

    def elaborate(self, tcltarget):
        tcltarget.write('\t#--- {} {}\n'.format(self.cptype, self.name))
        if self.key_BURST_ON_BURST_BOUNDARIES_ONLY:
            tcltarget.write('\tset {}_bobbo [get_parameter_value {}]\n'
                            .format(self.name, self.key_BURST_ON_BURST_BOUNDARIES_ONLY))
            tcltarget.write('\tset_interface_property {0} burstOnBurstBoundariesOnly ${0}_bobbo\n'
                            .format(self.name))

        if self.key_HOLD_TIME:
            tcltarget.write('\tset {}_ht [get_parameter_value {}]\n'
                            .format(self.name, self.key_HOLD_TIME))
            tcltarget.write('\tset_interface_property {0} holdTime ${0}_ht\n'
                            .format(self.name))

        if self.key_LINE_WRAP_BURSTS:
            tcltarget.write('\tset {}_lwb [get_parameter_value {}]\n'
                            .format(self.name, self.key_LINE_WRAP_BURSTS))
            tcltarget.write('\tset_interface_property {0} holdTime ${0}_lwb\n'
                            .format(self.name))

        if self.key_MAXIMUM_PENDING_READ_TRANSACTIONS:
            tcltarget.write('\tset {}_mprt [get_parameter_value {}]\n'
                            .format(self.name, self.key_MAXIMUM_PENDING_READ_TRANSACTIONS))
            tcltarget.write('\tset_interface_property {0} maximumPendingReadTransactions ${0}_mprt\n'
                            .format(self.name))

        if self.key_READ_LATENCY:
            tcltarget.write('\tset {}_rl [get_parameter_value {}]\n'
                            .format(self.name, self.key_READ_LATENCY))
            tcltarget.write('\tset_interface_property {0} readLatency ${0}_rl\n'
                            .format(self.name))

        if self.key_READ_WAIT_TIME:
            tcltarget.write('\tset {}_rwt [get_parameter_value {}]\n'
                            .format(self.name, self.key_READ_WAIT_TIME))
            tcltarget.write('\tset_interface_property {0} readWaitTime ${0}_rwt\n'
                            .format(self.name))

        if self.key_SETUP_TIME:
            tcltarget.write('\tset {}_sut [get_parameter_value {}]\n'
                            .format(self.name, self.key_SETUP_TIME))
            tcltarget.write('\tset_interface_property {0} setupTime ${0}_sut\n'
                            .format(self.name))

        if self.key_WRITE_WAIT_TIME:
            tcltarget.write('\tset {}_wwt [get_parameter_value {}]\n'
                            .format(self.name, self.key_WRITE_WAIT_TIME))
            tcltarget.write('\tset_interface_property {0} writeWaitTime ${0}_wwt\n'
                            .format(self.name))

        if self.key_BRIDGES_TO_MASTER and self.cptype == 'MMSlave':
            tcltarget.write('\tset {}_btm [get_parameter_value {}]\n'
                            .format(self.name, self.key_BRIDGES_TO_MASTER))
            tcltarget.write('\tset_interface_property {0} bridgesToMaster ${0}_btm\n'
                            .format(self.name))

        if self.key_WIDTH_A:
            if self.genericslist.isderived(self.key_WIDTH_A):
                tcltarget.write('\tset {0}_a_width [ lindex $l [expr [lsearch $l "{1}"] +1]]\n'
                                .format(self.name, self.key_WIDTH_A))
                tcltarget.write('\tset_parameter_value {1} ${0}_a_width \n'
                                .format(self.name, self.key_WIDTH_A))
                # mark that the derived key has been used
                self.genericslist.markderived(self.key_WIDTH_A)
            else:
                tcltarget.write('\tset {}_a_width [get_parameter_value {}]\n'
                                .format(self.name, self.key_WIDTH_A))

            tcltarget.write('\tadd_interface_port {0} {1} address {2} ${0}_a_width\n'
                            .format(self.name, self.address, 'Input' if self.cptype == 'MMSlave' else 'Output'))

        if self.key_WIDTH_MM_D:
            tcltarget.write('\tset {}_dwidth [get_parameter_value {}]\n'
                            .format(self.name, self.key_WIDTH_MM_D))
            if self.wr:
                tcltarget.write('\tadd_interface_port {0} {1} readdata {2} ${0}_dwidth\n'.format(
                    self.name, self.readdata, 'Input' if self.cptype == 'MMMaster' else 'Output'))
            if self.rd:
                tcltarget.write('\tadd_interface_port {0} {1} writedata {2} ${0}_dwidth\n'.format(
                    self.name, self.writedata, 'Input' if self.cptype == 'MMSlave' else 'Output'))

        if self.burstcount and self.key_MAXIMUM_BURSTCOUNT:
            if self.key_WIDTH_BURSTCOUNT:
                tcltarget.write('\tset {}_wbc [get_parameter_value {}]\n'
                                .format(self.name, self.key_WIDTH_BURSTCOUNT))
                tcltarget.write('\tadd_interface_port {0} {1} burstcount {2} ${0}_wbc\n'
                                .format(self.name, self.burstcount, 'Input' if self.cptype == 'MMSlave' else 'Output'))
            else:
                tcltarget.write('\tset {}_mbc [get_parameter_value {}]\n'
                                .format(self.name, self.key_MAXIMUM_BURSTCOUNT))
                tcltarget.write('\tadd_interface_port {0} {1} burstcount {2} $[log2ceiling {0}_mbc]\n'
                                .format(self.name, self.burstcount, 'Input' if self.cptype == 'MMSlave' else 'Output'))


class Conduit(ConnectionPoint):

    def __init__(self, cptype, genericslist, decl):
        ConnectionPoint.__init__(self)
#         print(decl)
        self.cptype = cptype
        self.genericslist = genericslist
        self.associatedclock = None
        self.associatedreset = None
        # unpack
        self.name, decl_cr, decl_sigs = decl
        if decl_cr:
            self.associatedclock = decl_cr[0]
            if len(decl_cr) > 1:
                self.associatedreset = decl_cr[1]

        # decl_sigs must be a (list, tuple) of tuple(s)
        self.siglist = []
        for sig in decl_sigs:
            sig_key = None
            sig_val = None
            # check the width spec
            if isinstance(sig[2], int):
                sig_val = sig[2]
            else:
                # must be a string
                if sig[2].isdigit():
                    sig_val = int(sig[2])
                else:
                    sig_key = sig[2]

            self.siglist.append((sig[0], sig[1], sig[2], sig_key, sig_val))

    def makesignals(self):
        sigs = []
        for sig in self.siglist:
            if sig[3] is not None:
                sigs.append(
                    myhdl.Signal(myhdl.intbv(0)[self.genericslist.value(sig[3]):]))
            else:
                sigs.append(myhdl.Signal(myhdl.intbv(0)[sig[4]:]))
        return sigs if len(sigs) > 1 else sigs[0]

    def show(self):
        global indent
        print('{:{width}}Connection Point {}: {}, associated clock: {}, associated reset: {}' .format(
            ' ', self.cptype, self.name, self.associatedclock, self.associatedreset, width=indent))
        indent += 4
        for item in self.siglist:
            print('{:{width}}{} {} {}' .format(
                ' ', item[0], item[1], item[2], width=indent))
        indent -= 4

    def tclconnectionpoint(self, tcltarget):
        tcltarget.write('# +-----------------------------------\n')
        tcltarget.write('# |connection point {}\n'
                        .format(self.name))
        tcltarget.write('# |\n')
        tcltarget.write('add_interface {} conduit end\n' .format(self.name))
        # verbatim
        tcltarget.write(
            'set_interface_property {} ENABLED true\n'.format(self.name))

        # set_interface_property Sequence associatedClock Clk
        # set_interface_property Sequence associatedReset Reset
        if self.associatedclock:
            tcltarget.write('set_interface_property {} associatedClock {}\n' .format(
                self.name, self.associatedclock))
            if self.associatedreset:
                tcltarget.write('set_interface_property {} associatedReset {}\n' .format(
                    self.name, self.associatedreset))

        for sig in self.siglist:
            if sig[3] is None:
                # fixed width
                tcltarget.write('add_interface_port {} {} export {} {}\n'.format(
                    self.name, sig[0], sig[1], sig[4]))

        tcltarget.write('# |\n' +
                        '# |\n' +
                        '# +-----------------------------------\n\n')

    def elaborate(self, tcltarget):
        tcltarget.write('\t#--- {} {}\n'.format(self.cptype, self.name))
        for sig in self.siglist:
            if sig[3] is not None:
                # looking up
                if self.genericslist.isderived(sig[3]):
                    tcltarget.write('\tset {0}_{1} [ lindex $l [expr [lsearch $l "{2}"] +1]]\n'
                                    .format(self.name, sig[0], sig[3]))
                    tcltarget.write('\tset_parameter_value {2} ${0}-{1} \n'
                                    .format(self.name, sig[0], sig[3]))
                else:
                    tcltarget.write('\tset {}_{} [get_parameter_value {}]\n'
                                    .format(self.name, sig[0], sig[3]))
                    # add_interface_port SequenceB SequenceTimeB export Output
                    # 16
                    print(sig)
                    tcltarget.write('\tadd_interface_port {0} {1} export {2} ${0}_{1}\n'
                                    .format(self.name, sig[0], sig[1]))


if __name__ == '__main__':
    # ''' here we add some tests '''
    #     connectionpointlist           ::= (
    #                                           connectionpointdefinition+
    #                                       )
    #
    #     connectionpointdefinition    ::= (                        # open parenthesis to start tuple
    #                                           ( 'Clock' ,                 ( name , clockparams    )) |
    #                                           ( 'Reset' ,                 ( name , resetparms    )) |
    #                                           ( 'Sink' | 'Source' ,       ( name , stparams       )) |
    #                                           ( 'MMSlave' | 'MMMaster' , ( name , mmparams       )) |
    #                                           ( 'Conduit' ,               ( name , conduitparams ))
    #                                       )                          # final parenthesis to close tuple
    #
    #     clockparams                    ::= idclock INT
    #
    #     resetparams                    ::= idreset , idclock [, 'DEASSERT' | 'BOTH' | 'NONE' ]
    #
    #     stparams                       ::= associatedclockreset , stdata , [ sthandshake , [stpackets , [ stchannel [ sterror ]]]]
    #
    #     mmparams                       ::= t.b.d
    #
    #     conduitparams                 ::= t.b.d
    #
    #     associatedclockreset          ::= ( idclock , idreset )
    #
    #     stdata                        ::= ( signame , sigwidth [ , extsigwidth [, BIG_ENDIAN | LITTLE_ENDIAN | None]] )
    #
    #     sthandshake                    ::= None |  NO_READY | NO_VALID
    #
    #     stpackets                     ::= ( generic | True | None , [generic | True | None] )
    #
    #     stchannel                     ::= extsigwidth , [sigwidth , ]
    #
    #     sterror                        ::= extsigwidth
    #
    #     name                           ::= id
    #
    #     signame                        ::= id
    #
    #     sigwidth                       ::= generic | INT
    #
    #     extsigwidth                    ::= generic | INT | None
    #
    #     sdsdsad                        ::= generic | True | None
    #
    #     generic                        ::= id
    #
    #     idclock                        ::= id
    #
    #     idreset                        ::= id
    #
    #     INT                            ::= numeric+ | ' numeric+ '
    #
    #     id                             ::= ' alpha+alphanumeric* '
    #
    #     NO_READY , NO_VALID           ::= 1 , 2
    #
    #     BIG_ENDIAN , LITTLE_ENDIAN    ::= 1 , 2
    #

    cps = ConnectionPoints(None,  # no generics ...
                           (('Clock', ('Clk', 0)),
                            ('Reset', ('Reset', 'Clk')),
                            # a minimal ST-sink
                            ('Sink', ('In0', ('Clk', 'Reset'),
                                      ('D0', 'WIDTH_D', 'WIDTH_D'))),
                            # with forced Packet signalsNone
                            ('Sink', ('In1', ('Clk', 'Reset'),
                                      ('D1', 'WIDTH_D'), (True, ))),
                            # and forced Empty signals
                            ('Sink', ('In2', ('Clk', 'Reset'),
                                      ('D2', 'WIDTH_D'), (True, True))),
                            # with selectable Packet / Empty signals
                            ('Sink', ('In3', ('Clk', 'Reset'), ('D3', 'WIDTH_D',
                                                                'WIDTH_SYMBOL_D3'), ('D3_USE_PACKETS', 'D3_USE_EMPTY'))),
                            # adding channel info
                            ('Sink', ('In4', ('Clk', 'Reset'), ('D4', 'WIDTH_D'),
                                      (True, False), ('D4_USE_CHANNEL', 'D4_MAX_CHANNEL'))),
                            ('Clock', ('ClkOut', 0)),
                            ('Reset', ('ResetOut', 'ClkOut')),
                            # alternate form of defining symbolwidth == width
                            ('Source', ('Out0', ('ClkOut', 'ResetOut'),
                                        ('Q0', 'WIDTH_Q', None))),
                            # adding an errors output
                            ('Source', ('Out1', ('ClkOut', 'ResetOut'), ('Q1',
                                                                         'WIDTH_Q'), (True, ), (None, ), ('Q1_WIDTH_ERROR', ))),
                            ('Conduit', ('Sequence'), ('ClkOut', 'ResetOut'), ((
                                'SequenceID', 'Input', 'WIDTH_SEQUENCE_ID'), ('Time', 'Input', '16')))
                            )
                           )
    cps.show()

    sys.exit(0)
