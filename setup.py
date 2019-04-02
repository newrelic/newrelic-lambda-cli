#!/usr/bin/env python3
from setuptools import setup, find_packages

setup(
    name='iopipe_install',
    version='0.1',
    python_requires='>=3.3',
    packages=find_packages(),
    install_requires=[
        'click',
        'boto3',
        'requests'
    ],
    entry_points='''
        [console_scripts]
        iopipe-install=iopipe_install.cli:main
    ''',
)
