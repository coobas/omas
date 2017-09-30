from __future__ import absolute_import, print_function, division, unicode_literals

#-----------------
# external imports
#-----------------
import xarray
import os
import sys
import glob
import json
import copy
import pandas
from collections import OrderedDict
import re
import numpy
from pprint import pprint
from hashlib import md5
import uncertainties

#--------------------------------------------
# configuration of directories and IMAS infos
#--------------------------------------------
imas_json_dir=os.path.abspath(str(os.path.dirname(unicode(__file__, sys.getfilesystemencoding())))+'/imas_structures/')

separator='.'

if 'IMAS_VERSION' in os.environ:
    imas_version=os.environ['IMAS_VERSION']
else:
    imas_version='3.10.1'
if 'IMAS_PREFIX' in os.environ:
    imas_html_dir=os.environ['IMAS_PREFIX']+'/share/doc/imas/'
else:
    imas_html_dir='/Users/meneghini/tmp/imas'
imas_html_dir=os.path.abspath(imas_html_dir)

default_omas_mds_server=['atlas.gat.com','127.0.0.1:63555'][1]
