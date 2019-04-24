#!/usr/bin/env python3
from setuptools import setup, find_packages

setup(
    name='iopipe-cli',
    version='0.1.1',
    python_requires='>=3.3',
    packages=find_packages(),
    install_requires=[
        'click',
        'boto3',
        'requests',
        'pyjwt'
    ],
    tests_require=[
        "coverage==5.0a2",
        "mock",
        "more-itertools<6.0.0",
        "pytest==4.1.0",
        "pytest-benchmark==3.2.0",
        "pytest-cov==2.6.1",
        "requests",
    ],
    entry_points={
        'console_scripts': [
            'iopipe = iopipe_cli.cli:main',
        ],
    }
)
