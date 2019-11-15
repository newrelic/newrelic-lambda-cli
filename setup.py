#!/usr/bin/env python3

import os

from setuptools import find_packages, setup

try:
    from pypandoc import convert

    README = convert("README.md", "rst")
except (ImportError, OSError):
    README = open(os.path.join(os.path.dirname(__file__), "README.md"), "r").read()

setup(
    name="newrelic-lambda-layers",
    version="0.1.0",
    python_requires=">=3.3",
    description="cli utility for managing and instrumenting serverless applications",
    long_description=README,
    author="IOpipe",
    author_email="dev@iopipe.com",
    url="https://github.com/iopipe/newrelic-lambda-layers-cli",
    packages=find_packages(exclude=("tests", "tests.*")),
    install_requires=["boto3", "click", "gql", "requests", "tabulate"],
    setup_requires=["pytest-runner"],
    tests_require=["coverage", "pytest", "pytest-cov", "requests"],
    entry_points={
        "console_scripts": ["newrelic-layers = newrelic_lambda_layers.cli:main"]
    },
    include_package_data=True,
)
