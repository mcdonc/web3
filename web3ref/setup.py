"""Distutils setup file"""

import ez_setup
ez_setup.use_setuptools()

from setuptools import setup

setup(
    name='web3ref',
    version='0.0',
    description="Web3 Reference Library",
    author="Chris McDonough (originally Phillip J. Eby's wsgiref)",
    author_email="web-sig@python.org",
    license="PSF or ZPL",
    url="http://pypi.python.org/pypi/web3ref",
    long_description = open('README.txt').read(),
    test_suite  = 'web3ref.tests',
    packages    = ['web3ref'],
    )

