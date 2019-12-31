import os

from setuptools import find_packages, setup

try:
    from pypandoc import convert

    README = convert("README.md", "rst")
except (ImportError, OSError):
    README = open(os.path.join(os.path.dirname(__file__), "README.md"), "r").read()

setup(
    name="newrelic-lambda-cli",
    version="0.1.7",
    python_requires=">=3.3",
    description="A CLI to install the New Relic AWS Lambda integration and layers.",
    long_description=README,
    long_description_content_type="text/x-rst",
    author="New Relic",
    author_email="serverless-dev@newrelic.com",
    url="https://github.com/newrelic/newrelic-lambda-cli",
    packages=find_packages(exclude=("tests", "tests.*")),
    install_requires=["boto3", "click", "colorama", "gql", "requests", "tabulate"],
    setup_requires=["pytest-runner"],
    tests_require=["coverage", "pytest", "pytest-click", "pytest-cov", "requests"],
    entry_points={
        "console_scripts": ["newrelic-lambda = newrelic_lambda_cli.cli:main"]
    },
    include_package_data=True,
    zip_safe=False,
)
