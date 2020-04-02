import os

from setuptools import find_packages, setup

README = open(os.path.join(os.path.dirname(__file__), "README.md"), "r").read()

setup(
    name="newrelic-lambda-cli",
    version="0.2.1",
    python_requires=">=3.3",
    description="A CLI to install the New Relic AWS Lambda integration and layers.",
    long_description=README,
    long_description_content_type="text/markdown",
    author="New Relic",
    author_email="serverless-dev@newrelic.com",
    url="https://github.com/newrelic/newrelic-lambda-cli",
    packages=find_packages(exclude=("tests", "tests.*")),
    install_requires=["boto3", "click", "colorama", "gql", "requests", "tabulate"],
    setup_requires=["pytest-runner"],
    tests_require=["moto", "pytest", "requests"],
    entry_points={
        "console_scripts": ["newrelic-lambda = newrelic_lambda_cli.cli:main"]
    },
    include_package_data=True,
    zip_safe=False,
)
