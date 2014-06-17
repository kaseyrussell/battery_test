""" Test a single battery through repeated cycling.
This assumes:

1) Measuring battery voltage directly using the analog input ain_batt

2) A current sink attached to the battery controlled by the analog out outp_sink

3) A current source attached to the battery controlled by analog out outp_src

This uses the Labjack and BatteryTest classes from the labjack module.

KJR, GoodLux Tech., June 2014
"""
from __future__ import division
import matplotlib.pyplot as plt
import datetime
import requests
import json
import base64
import sys
import numpy as np

plt.close(1)
fig = plt.figure(num=1)
ax = fig.add_subplot(111)
ax.set_xlabel("Time (hours)")
ax.set_ylabel("Battery voltage (V)")

import h5py
import datetime
import numpy as np
import time

with h5py.File('testdata_BBMx.hdf5', 'r') as f:
    time   = f['time'][:]
    volts  = f['voltage'][:]
    cycle  = f['cycle'][:]
    dtype  = f['type'][:]

current_cycle = cycle[0]
tlist, vlist = [], []
for t,v,c in zip(time,volts,cycle):
    if c != current_cycle and len(vlist)>0:
        ax.plot(tlist, vlist, '-')
        tlist, vlist = [], []
    tlist.append(float(t)/3600.0)
    vlist.append(v)

ax.plot(tlist, vlist, '-')
fig.show()
fig.canvas.draw()
