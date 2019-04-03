#!/usr/bin/env python3
from setuptools import setup, find_packages

setup(
    name='iopipe-cli',
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
        iopipe=iopipe_cli.cli:main
    ''',
)
