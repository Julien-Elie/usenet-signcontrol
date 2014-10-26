#!/bin/sh
#
# Support script to generate documentation for signcontrol.py, suitable
# to be read as text.

pod2text --sentence --loose ../signcontrol.py > ../README
