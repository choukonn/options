#!/usr/bin/python3
# vim: ts=4 sts=4 sw=4


import sys
import pathlib
import re

from logging import getLogger, DEBUG, INFO, WARNING
logger = getLogger('days_renkei').getChild(__name__)

# myapp
#from mod import common as cmn
import renkei_tools_py.ext

