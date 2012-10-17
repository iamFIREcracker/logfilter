#!/usr/bin/env python

import os
from setuptools import find_packages
from setuptools import setup


VERSION = '0.5.0'
NAME = 'logfilter'
PACKAGES = [NAME]
DESCRIPTION = 'Poll log files for updates and highlight words based on regexp filters'
readme = os.path.join(os.path.dirname(__file__), 'README.rst')
LONG_DESCRIPTION = open(readme).read()
requirements = os.path.join(os.path.dirname(__file__), 'requirements.txt')
INSTALL_REQUIRES = open(requirements).read().split()

URL = 'https://bitbucket.org/iamFIREcracker/logfilter'
DOWNLOAD_URL = 'http://pypi.python.org/pypi/logfilter'

CLASSIFIERS = [
    'Development Status :: 4 - Beta',
    'Environment :: Other Environment',
    'Intended Audience :: Developers',
    'Intended Audience :: Science/Research',
    'Intended Audience :: System Administrators',
    'License :: OSI Approved :: BSD License',
    'Operating System :: OS Independent',
    'Programming Language :: Python :: 2.7',
    'Programming Language :: Python :: 3.2',
    'Topic :: Text Processing :: Filters',
    'Topic :: Utilities',
]

AUTHOR = 'Matteo Landi'
AUTHOR_EMAIL = 'matteo@matteolandi.net'
KEYWORDS = "log filter grep tail".split(' ')

params = dict(
    name=NAME,
    version=VERSION,
    packages=find_packages(),
    entry_points={
        'gui_scripts': ['logfilter = logfilter.logfilter:_main'],
    },
    install_requires=INSTALL_REQUIRES,

    # metadata for upload to PyPI
    author=AUTHOR,
    author_email=AUTHOR_EMAIL,
    description=DESCRIPTION,
    long_description=LONG_DESCRIPTION,
    license='BSD',
    keywords=KEYWORDS,
    url=URL,
    download_url=DOWNLOAD_URL,
    classifiers=CLASSIFIERS,
    requires=INSTALL_REQUIRES,
)

setup(**params)
