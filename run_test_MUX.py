""" Test a bunch of batteries using a MUX.

This uses the Labjack and BatteryTest classes from the labjack module.

Copyright 2014 Kasey J. Russell, GoodLux Tech., June 2014
"""
from __future__ import division
import labjack


# list the battery names and their respective MUX output ports (Y0 is denoted 0)
batteries = [
    dict( id="BBM09_pulsed", mux=0 ),
    dict( id="BBM10_pulsed", mux=1 ),
    dict( id="BBM11_pulsed", mux=2 ),
    dict( id="BBM12_pulsed", mux=3 ),
    dict( id="BBM13_pulsed", mux=4 ),
    ]

d   = labjack.Labjack()

mx = labjack.MUXTest(d, batteries, sample_interval=10.0)
mx.run_test()

d.close()

