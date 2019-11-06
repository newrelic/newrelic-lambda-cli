# newrelic-lambda-layers-cli

A CLI to install New Relic AWS LAmbda layers.

## Features

* Installs and configures a New Relic AWS Lambda layer onto your AWS Lambda function
* Automatically selects the correct layer for your function's runtime and region
* Wraps your function without requiring a code change
* Supports Node.js and Python AWS LAmbda runtimes
* Easily uninstall the layer with a single command

## Runtimes Supported

* nodejs10.x
* python2.7
* python3.6
* python3.7

## Requirements

* Set up the [New Relic AWS Integration](https://docs.newrelic.com/docs/serverless-function-monitoring/aws-lambda-monitoring/get-started/enable-new-relic-monitoring-aws-lambda#enable-process)
* Retrieve your [New relic Account ID](https://docs.newrelic.com/docs/accounts/install-new-relic/account-setup/account-id)

## Installation

```bash
pip install newrelic-lambda-layers-cli
```

Or clone this repo and run:

```bash
python setup.py install
```

## Usage

### Install Layer

```bash
newrelic-layers lambda install --function <name or arn> --account-id <new relic account id>
```

### Uninstall Layer

```bash
newrelic-layers lambda uninstall --function <name or arn>
```

### List Functions

```bash
newrelic-layers lambda list
```

List functions with layer installed:

```bash
newrelic-layers lambda list --filter installed
```
