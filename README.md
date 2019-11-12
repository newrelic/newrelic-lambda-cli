# newrelic-lambda-layers-cli

A CLI to install the New Relic AWS integration and Lambda layers.

## Features

* Install the New Relic AWS integration
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

* Retrieve your [New relic Account ID](https://docs.newrelic.com/docs/accounts/install-new-relic/account-setup/account-id) and [User API Key](https://docs.newrelic.com/docs/apis/get-started/intro-apis/types-new-relic-api-keys#user-api-key)

## Installation

```bash
pip install newrelic-lambda-layers-cli
```

Or clone this repo and run:

```bash
python setup.py install
```

## Usage

### Install Integration

```bash
newrelic-layers integration install \
    --nr-account-id <account id> \
    --nr-api-key <api key> \
    --linked-account-name <linked account name>
```

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
