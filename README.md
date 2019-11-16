# newrelic-lambda-cli

A CLI to install the New Relic AWS Lambda integration and layers.

## Features

* Installs the New Relic AWS integration
* Installs and configures a New Relic AWS Lambda layer onto your AWS Lambda functions
* Automatically selects the correct New Relic layer for your function's runtime and region
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
pip install newrelic-lambda-cli
```

Or clone this repo and run:

```bash
python setup.py install
```

## Usage

### Install AWS Lambda Integration

```bash
newrelic-lambda integration install \
    --nr-account-id <account id> \
    --nr-api-key <api key> \
    --linked-account-name <linked account name>
```

### Install Layer

```bash
newrelic-lambda layer install --function <name or arn> --account-id <new relic account id>
```

### Uninstall Integration

```bash
newrelic-lambda integration uninstall
```

### Uninstall Layer

```bash
newrelic-lambda layer uninstall --function <name or arn>
```

### List Functions

```bash
newrelic-lambda function list
```

List functions with layer installed:

```bash
newrelic-lambda function list --filter installed
```

## Contributing

Contributions are welcome. We use the [black](https://github.com/ambv/black) code formatter.

```bash
pip install black
```

We recommend using it with [pre-commit](https://pre-commit.com/#install):

```bash
pip install pre-commit
pre-commit install
```

Using these together will auto format your git commits.

## Running Tests

```bash
python setup.py test
```
