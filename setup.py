#!/usr/bin/env python3
from setuptools import setup, find_packages
import os

try:
    from pypandoc import convert

    README = convert("README.md", "rst")
except (ImportError, OSError):
    README = open(os.path.join(os.path.dirname(__file__), "README.md"), "r").read()

setup(
    name='iopipe-cli',
    version='0.1.3',
    python_requires='>=3.3',
    description="cli utility for managing and instrumenting serverless applications",
    long_description=README,
    author="IOpipe",
    author_email="dev@iopipe.com",
    url="https://github.com/iopipe/iopipe-cli",
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
