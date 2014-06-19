battery_test
============

Python code to test charge/discharge of multiple Li-Poly batteries using a Labjack USB DAQ.

BE CAREFUL CHARGING LITHIUM BATTERIES. If they burst into flames, it's not my fault.
I'm testing tiny batteries (15 mAh), and they have protection circuits built in.

If you are using this to TEST MORE THAN ONE BATTERY IN PARALLEL, it's very
important that each battery has a protection circuit to prevent over charge and
over discharge. This software does not protect against that.

I don't have the hardware to individually charge/discharge multiple batteries 
(only measure voltage individually), so I base the charge/discharge enpoints
on the least charged / most charged battery (respectively). I am assuming that
the protection circuit on each battery will protect the outliers. 

This software uses the Labjack U12 multifunction DAQ with USB:
http://labjack.com/u12

And it requires the U12 class from the LabJackPython module from LabJack:
http://labjack.com/support/labjackpython
