# Qgen  
## A Framework for Building and Using Qsys Components with MyHDL
---
## Introduction
This module is an extension to [MyHDL](http://www.myhdl.org/start/overview.html) to create components for use with [Altera](http://www.altera.com/)'s [Qsys](http://www.altera.com/products/software/quartus-ii/subscription-edition/qsys/qts-qsys.html).  
Aside from using the fantastic MyHDL to describe the logic it allows you to automatically generate the necessary xxx\_hw.tcl file used by Qsys' GUI to represent your component. The generated xxx\_hw.tcl file has both an _Elaborate()_ and a _Generate()_ call back that will ultimately call upon the Python/MyHDL code to:
 * validate and calculate possibly derived parameters
 * convert the MyHDL Hardware Description to the customised VHDL (or Verilog) for synthesis

## Diving in at the Deep End
This is  a minimal example for such an Qsys Avalon-ST component:  
It takes a stream and swaps the _elements_ in the data

```python
'''
Created on 24 Dec 2015

@author: Josy
'''
from __future__ import print_function

import random

import myhdl

from Utilities import hdlutils
from Utilities import SimulateAvalon
from Utilities.Qgen import Qgen


def ST_elementswap(WIDTH_ELEMENT, SWAPS,
                Clk, Reset,
                DData, DSoP, DEoP, DValid, DReady,
                QData, QSoP, QEoP, QValid, QReady):

    ''' we swap the elements of the incoming data '''
    # although this is a  strictly combinatorial module, we still
    # need a clock and a reset to allow Qsys to validate the connection
    
    @myhdl.always_comb
    def bs():
        ''' the swapping is relatively simple '''
        for i in range(SWAPS):
            QData.next[(i + 1) * WIDTH_ELEMENT : i * WIDTH_ELEMENT] = \
                    DData[(SWAPS - i) * WIDTH_ELEMENT : (SWAPS - 1 - i) * WIDTH_ELEMENT ]

        QSoP.next   = DSoP
        QEoP.next   = DEoP
        QValid.next = DValid
        DReady.next = QReady

    return bs


def tb_ST_elementswap( q ):
    ''' the test-bench for our element swapper '''
    Clk = myhdl.Signal(bool(0))
    Reset = myhdl.ResetSignal(0, active=1, async=True)
    DData, DSoP, DEoP, _, _, _, DValid, DReady = q.makesignals('In')
    QData, QSoP, QEoP, _, _, _, QValid, QReady = q.makesignals('Out')

    dut = ST_elementswap(q.genericvalue( 'WIDTH_ELEMENT' ), q.genericvalue( 'SWAPS' ), Clk, Reset,
                         DData, DSoP, DEoP, DValid, DReady,
                         QData, QSoP, QEoP, QValid, QReady)

    # testdata
    random.seed("We want repeatable randomness")
    MAX_DATA = 2 ** q.genericvalue( 'WIDTH_DQ' ) - 1
    TEST_SAMPLES = 32
    testdata = [ random.randint(0,MAX_DATA)  for _ in range( TEST_SAMPLES )]

    ClkCount = myhdl.Signal(myhdl.intbv(0)[32:])
    tCK = 20

    @myhdl.instance
    def clkgen():
        yield hdlutils.genClk(Clk, tCK, ClkCount)

    @myhdl.instance
    def resetgen():
        yield hdlutils.genReset(Clk, tCK, Reset)

    @myhdl.instance
    def stimulusin():
        yield SimulateAvalon.STfeed(Clk, tCK, DReady, DValid, DData, testdata, DSoP, DEoP, DELAY=10, MODE="None")
        yield hdlutils.delayclks(Clk, tCK, 10)
        raise myhdl.StopSimulation

    @myhdl.instance
    def stimulusout():
        yield SimulateAvalon.STbackpressure(Clk, tCK, QReady, "None")

    return dut, clkgen, resetgen, stimulusin, stimulusout


def convert( q , targethdl):
    Clk = myhdl.Signal(bool(0))
    Reset = myhdl.ResetSignal(0, active=1, async=True)
    DData, DSoP, DEoP, _, _, _, DValid, DReady = q.makesignals('In')
    QData, QSoP, QEoP, _, _, _, QValid, QReady = q.makesignals('Out')

    myhdl.toVHDL( ST_elementswap, q.genericvalue( 'WIDTH_ELEMENT' ), q.genericvalue( 'SWAPS' ) , 
                                Clk, Reset,
                                DData, DSoP, DEoP, DValid, DReady,
                                QData, QSoP, QEoP, QValid, QReady)

if __name__ == '__main__':

    def elaborate(qsysargdict):
        ''' the 'elaborate' function is called upon by Qsys while elaborating user input
            it calculates 'derived' parameters
        '''
        lwidthdq = int(qsysargdict['WIDTH_DQ'])
        lswaps = int(qsysargdict['SWAPS'])
        lwidthelement = int(lwidthdq / lswaps)
        if lwidthelement * lswaps != lwidthdq:
            lwidthelement = 0

        return 'WIDTH_ELEMENT', lwidthelement


    Qgen.Qgen('ST_elementswap',
              # parameters
              (('WIDTH_DQ', ('Natural', 32)),
               ('SWAPS', ('Natural', 4)),
               ('WIDTH_ELEMENT', ('Natural', 8 , (1, 4096)), True) # derived to show whether the swapping may work
              ),
              # connection points
              (('Clock', ('Clk', 0)),
               ('Reset', ('Reset', 'Clk', 'DEASSERT' ) ),
               ('Sink', ('In', ('Clk', 'Reset'), ('D', 'WIDTH_DQ',), ( True, ), )),
               ('Source', ('Out', ('Clk', 'Reset'), ('Q', 'WIDTH_DQ',), ( True, ), )),
              ),
              testbench = (30000, tb_ST_elementswap),
              convert = convert,
              elaborate = elaborate,
              gentcl = ('1.0', 'Josy', 'C-Cam/Avalon')
              )
    
```

When we run this module without any arguments Qgen will first run the testbench, then convert into VHDL (or Verilog), and finally generate the xxx\_hw.tcl.  
The simulation output:
 
![image](C:\qdesigns\MyHDL\Source\avalon\ST_elementswap\tb_ST_elementswap_vcd.png)

The generated VHDL-code is as trivial as you have expected:

```VHDL
-- File: ST_elementswap.tmp
-- Generated by MyHDL 1.0dev
-- Date: Thu Dec 24 20:14:04 2015


library IEEE;
use IEEE.std_logic_1164.all;
use IEEE.numeric_std.all;
use std.textio.all;

use work.pck_myhdl_10.all;

entity ST_elementswap is
	port(
		Clk    : in  std_logic;
		Reset  : in  std_logic;
		DData  : in  unsigned(31 downto 0);
		DSoP   : in  std_logic;
		DEoP   : in  std_logic;
		DValid : in  std_logic;
		DReady : out std_logic;
		QData  : out unsigned(31 downto 0);
		QSoP   : out std_logic;
		QEoP   : out std_logic;
		QValid : out std_logic;
		QReady : in  std_logic
	);
end entity ST_elementswap;
-- we swap the elements of the incoming data 

architecture MyHDL of ST_elementswap is
begin

	-- the swapping is relatively simple 
	ST_elementswap_bs : process(DEoP, DData, DSoP, DValid, QReady) is
	begin
		for i in 0 to 4 - 1 loop
			QData(((i + 1) * 8) - 1 downto (i * 8)) <= DData(((4 - i) * 8) - 1 downto (((4 - 1) - i) * 8));
		end loop;
		QSoP   <= DSoP;
		QEoP   <= DEoP;
		QValid <= DValid;
		DReady <= QReady;
	end process ST_elementswap_bs;

end architecture MyHDL;
```


Here is the ST\_elementswap\_hw.tcl:

```tcl
# ST_elementswap_hw.tcl generated by C-Cam Technologies
# UTC: 24/12/2015 19:14
# Do Not Modify -- or at your own risk :)

package require -exact sopc 11.0

#
# module _toplevelname_
#
set_module_property NAME ST_elementswap
set_module_property VERSION 1.0
set_module_property INTERNAL false
set_module_property OPAQUE_ADDRESS_MAP true
set_module_property AUTHOR Josy
set_module_property DISPLAY_NAME ST_elementswap
set_module_property INSTANTIATE_IN_SYSTEM_MODULE true
set_module_property EDITABLE false
set_module_property ANALYZE_HDL false
set_module_property REPORT_TO_TALKBACK false
set_module_property ALLOW_GREYBOX_GENERATION false
set_module_property GROUP C-Cam/Avalon
set_module_property ELABORATION_CALLBACK Elaborate
set_module_property GENERATION_CALLBACK Generate

# +----------------------------------- 
# | parameters
# |

add_parameter WIDTH_DQ natural 32
set_parameter_property WIDTH_DQ DEFAULT_VALUE 32
set_parameter_property WIDTH_DQ DISPLAY_NAME WIDTH_DQ
set_parameter_property WIDTH_DQ TYPE natural
set_parameter_property WIDTH_DQ UNITS None
set_parameter_property WIDTH_DQ AFFECTS_ELABORATION true
set_parameter_property WIDTH_DQ AFFECTS_GENERATION true
set_parameter_property WIDTH_DQ HDL_PARAMETER false

add_parameter SWAPS natural 4
set_parameter_property SWAPS DEFAULT_VALUE 4
set_parameter_property SWAPS DISPLAY_NAME SWAPS
set_parameter_property SWAPS TYPE natural
set_parameter_property SWAPS UNITS None
set_parameter_property SWAPS AFFECTS_ELABORATION true
set_parameter_property SWAPS AFFECTS_GENERATION true
set_parameter_property SWAPS HDL_PARAMETER false

add_parameter WIDTH_ELEMENT natural 8
set_parameter_property WIDTH_ELEMENT DEFAULT_VALUE 8
set_parameter_property WIDTH_ELEMENT ALLOWED_RANGES { 1 4096 }
set_parameter_property WIDTH_ELEMENT DISPLAY_NAME WIDTH_ELEMENT
set_parameter_property WIDTH_ELEMENT TYPE natural
set_parameter_property WIDTH_ELEMENT UNITS None
set_parameter_property WIDTH_ELEMENT AFFECTS_ELABORATION true
set_parameter_property WIDTH_ELEMENT AFFECTS_GENERATION true
set_parameter_property WIDTH_ELEMENT HDL_PARAMETER false
set_parameter_property WIDTH_ELEMENT DERIVED true

# |
# +-----------------------------------

# +-----------------------------------
# | display items
# |
# |
# +-----------------------------------

# +-----------------------------------
# | connection point Clk
# |
add_interface Clk clock end
set_interface_property Clk clockRate 0
set_interface_property Clk ENABLED true
add_interface_port Clk Clk clk Input 1
# |
# +-----------------------------------

# +-----------------------------------
# | connection point Reset
# |
add_interface Reset reset end
set_interface_property Reset associatedClock Clk
set_interface_property Reset synchronousEdges DEASSERT
set_interface_property Reset ENABLED true
add_interface_port Reset Reset reset Input 1
# |
# +-----------------------------------

# +-----------------------------------
# | connection point In
# |
add_interface In avalon_streaming end
set_interface_property In associatedClock Clk
set_interface_property In associatedReset Reset
set_interface_property In firstSymbolInHighOrderBits true
set_interface_property In readyLatency 0
set_interface_property In ENABLED true
add_interface_port In DValid valid Input 1
add_interface_port In DReady ready Output 1
add_interface_port In DSoP startofpacket Input 1
add_interface_port In DEoP endofpacket Input 1
# |
# +-----------------------------------

# +-----------------------------------
# | connection point Out
# |
add_interface Out avalon_streaming start
set_interface_property Out associatedClock Clk
set_interface_property Out associatedReset Reset
set_interface_property Out firstSymbolInHighOrderBits true
set_interface_property Out readyLatency 0
set_interface_property Out ENABLED true
add_interface_port Out QValid valid Output 1
add_interface_port Out QReady ready Input 1
add_interface_port Out QSoP startofpacket Output 1
add_interface_port Out QEoP endofpacket Output 1
# |
# +-----------------------------------

# +----------------------------------------------------------------
# | Elaborate callback
proc Elaborate {} {
	send_message info "Current Directory: [pwd]"
	set command exec
	lappend command python [pwd]/ST_elementswap.py --QsysElaborate 
	lappend command WIDTH_DQ [get_parameter_value WIDTH_DQ ] 
	lappend command SWAPS [get_parameter_value SWAPS ] 
	set result [eval $command]
	# $result holds what was written to stdout
	# it should look along the line like: lwidth_d 10 lwidth_q 8
	# we don't care about '()[],' as we will strip them
	#send_message info  "QsysElaborate: OK -> <<<* $result *>>>"
	# now process the returns
	# split the result
	set r [string trim $result  "()[]" ]
	set l [list]
	foreach item $r {
		lappend l [string trim $item "',"]
	}
	foreach {name val} $l {
		send_message info  "$name $val"
	}
	#--- Sink In
	set In_d_width [ get_parameter_value WIDTH_DQ ]
	add_interface_port In DData data Input $In_d_width
	set_interface_property In symbolsPerBeat 1
	set_interface_property In dataBitsPerSymbol $In_d_width 
	#--- Source Out
	set Out_d_width [ get_parameter_value WIDTH_DQ ]
	add_interface_port Out QData data Output $Out_d_width
	set_interface_property Out symbolsPerBeat 1
	set_interface_property Out dataBitsPerSymbol $Out_d_width 
	#--- derived parameters that do not belong to a connection point
	set_parameter_value WIDTH_ELEMENT [ lindex $l [expr [lsearch $l "WIDTH_ELEMENT"] +1]]] 
}
# |
# +-----------------------------------

# +----------------------------------------------------------------
# | Generate callback
proc Generate {} {
	send_message info "Current Directory: [pwd]"
	set outdir [get_generation_property OUTPUT_DIRECTORY]
	set outputname [get_generation_property OUTPUT_NAME]
	set targethdl [get_generation_property HDL_LANGUAGE]
	set command exec
	lappend command python [pwd]/ST_elementswap.py -l $targethdl --QsysGenerate 
	lappend command $outdir $outputname
	lappend command WIDTH_DQ [get_parameter_value WIDTH_DQ ] 
	lappend command SWAPS [get_parameter_value SWAPS ] 
	lappend command WIDTH_ELEMENT [get_parameter_value WIDTH_ELEMENT ] 
	send_message info "Generating using command: $command"
	eval $command
	add_file $outdir/$outputname.vhd {SYNTHESIS SIMULATION}
}
# |
# +-----------------------------------

# +----------------------------------------------------------------
# | utility functions
proc log2ceiling { num } {
	set val 0
	set i   1
	while { $i < $num } {
		set val [ expr $val + 1 ]
		set i   [ expr 1 << $val ]
	}
	if { $val == 0 } {
		set val 1
	}
	return $val;
}

```

And this is how Qsys sees our module:  

![image](C:\qdesigns\MyHDL\Source\avalon\ST_elementswap\tb_ST_elementswap_Qsys.png)

![image](C:\qdesigns\MyHDL\Source\avalon\ST_elementswap\tb_ST_elementswap_Qsys-system.png)

