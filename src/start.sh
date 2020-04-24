#!/bin/sh

# start the program
python /home/extensive/automateactions.py --start

# tailf on process
tail -f /home/extensive/ea/automateactions/data/logs/output.log
