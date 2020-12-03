#!/usr/bin/env python3

import sys, os
try:
  from setuptools import setup
except ImportError:
  from distutils.core import setup

if not sys.version_info[0] == 3:
    sys.exit("Python 2.x is not supported; Python 3.x is required.")

########################################

setup(name="stravacli",
      version="0.0.1",
      description="Command-line client for Strava",
      author="Daniel Lenski",
      author_email="dlenski@gmail.com",
      license='GPL v3 or later',
      install_requires=open('requirements.txt').readlines(),
      url="https://github.com/dlenski/stravacli",
      packages = ['stravacli'],
      entry_points={ 'console_scripts': [ 'stravaup=stravacli.stravaup:main' ] },
      test_suite='nose.collector',
      )
