""" Test a single battery through repeated cycling.
This assumes:

1) Measuring battery voltage directly using the analog input ain_batt

2) A current sink attached to the battery controlled by the analog out outp_sink

3) A current source attached to the battery controlled by analog out outp_src

This uses the Labjack and BatteryTest classes from the labjack module.

KJR, GoodLux Tech., June 2014
"""
from __future__ import division
import labjack
import matplotlib.pyplot as plt
import datetime
import time
import sys

d   = labjack.Labjack()

assert len(sys.argv) == 2, "Missing command line argument. Proper use is 'run <script> id=ExampleID' where ExampleID is the ID number of the battery under test."
if not "id=" in sys.argv[1]:
    raise ValueError("Need 'id=' argument to specify the ID number of the battery under test.")
battery_id = sys.argv[1].split("id=")[-1].strip()

battery_test  = labjack.BatteryTest(d, battery_id)
battery_test.off()
battery_test.run_test()

d.close()

