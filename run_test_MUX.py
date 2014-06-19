""" Test a bunch of batteries using a MUX.

This uses the Labjack and BatteryTest classes from the labjack module.

Copyright 2014 Kasey J. Russell, GoodLux Tech., June 2014
"""
from __future__ import division
import labjack


# list the battery names and their respective MUX output ports (Y0 is denoted 0)
batteries = [
    dict( id="BBM04r8", mux=0 ),
    dict( id="BBM05r8", mux=1 ),
    dict( id="BBM06r8", mux=2 ),
    dict( id="BBM07r8", mux=3 ),
    dict( id="BBM08r8", mux=4 ),
    ]

d   = labjack.Labjack()

mx = labjack.MUXTest(d, batteries)
mx.run_test()

d.close()

