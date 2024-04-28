#!/usr/bin/env python3

import sys
try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

if not sys.version_info[0] == 3:
    sys.exit("Python 2.x is not supported; Python 3.x is required.")

########################################

req = [
    (bits[-1], bits[0] if len(bits) > 1 else None)
    for bits in
    (l.rstrip().split('#egg=', 1) for l in open('requirements.txt'))
]

setup(
    name="stravacli",
    version="0.0.1",
    description="Command-line clients for Strava",
    author="Daniel Lenski",
    author_email="dlenski@gmail.com",
    license='GPL v3 or later',
    install_requires=[r[0] for r in req],
    dependency_links=[r[1] for r in req if r[1] is not None],
    extras_require={
        'stravadown': 'stravaweblib'
    },
    url="https://github.com/dlenski/stravacli",
    packages=['stravacli'],
    entry_points={'console_scripts': [
        'stravaup=stravacli.stravaup:main',
        'stravadown=stravacli.stravadown:main'
    ]},
    test_suite='nose.collector',
)
