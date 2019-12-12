# newrelic-lambda-cli

A CLI to install the New Relic AWS Lambda integration and layers.

## Features

* Installs the New Relic AWS Lambda integration onto your AWS account
* Installs and configures a New Relic AWS Lambda layer onto your AWS Lambda functions
* Automatically selects the correct New Relic layer for your function's runtime and region
* Wraps your AWS Lambda functions without requiring a code change
* Supports Node.js and Python AWS LAmbda runtimes
* Easily uninstall the AWS Lambda layer with a single command

## Runtimes Supported

* nodejs10.x
* nodejs12.x
* python2.7
* python3.6
* python3.7
* python3.8

## Requirements

* Python >= 3.3
* Retrieve your [New relic Account ID](https://docs.newrelic.com/docs/accounts/install-new-relic/account-setup/account-id) and [User API Key](https://docs.newrelic.com/docs/apis/get-started/intro-apis/types-new-relic-api-keys#user-api-key)

## Recommendations

* Install the [AWS CLI](https://github.com/aws/aws-cli) and configure your environment with `aws configure`

## Installation

```bash
pip install newrelic-lambda-cli
```

Or clone this repo and run:

```bash
python setup.py install
```

To update the CLI, run:

```
pip install --upgrade newrelic-lambda-cli
```

## Usage

### AWS Lambda Integration

#### Install Integration

In order to instrument your AWS Lambda functions using New Relic you must first install
the New Relic AWS Lambda integration and the log ingestion function in the AWS region
in which your Lambda functions are located. If you have Lambda functions located in multiple
regions you can run the command multiple times specifying the AWS regions with
`--aws-region <your aws region here>`. This command only needs to be run once per AWS
region. By default this command will look for a default AWS profile configured via the AWS CLI.

```bash
newrelic-lambda integrations install \
    --nr-account-id <account id> \
    --nr-api-key <api key> \
    --linked-account-name <linked account name>
```

| Option | Required? | Description |
|--------|-----------|-------------|
| `--nr-account-id` or `-a` | Yes | The [New Relic Account ID](https://docs.newrelic.com/docs/accounts/install-new-relic/account-setup/account-id) for this integration. Can also use the `NEW_RELIC_ACCOUNT_ID` environment variable. |
| `--nr-api-key` or `-k` | Yes | Your [New Relic User API Key](https://docs.newrelic.com/docs/apis/get-started/intro-apis/types-new-relic-api-keys#user-api-key). Can also use the `NEW_RELIC_API_KEY` environment variable. |
| `--linked-account-name` or `-l` | Yes | A label for the New Relic Linked ACcount. This is how this integration will appear in New Relic. |
| `--nr-region` | No | The New Relic region to use for the integration. Can use the `NEW_RELIC_REGION` environment variable. Defaults to `us`. |
| `--aws-profile` or `-p` | No | The AWS profile to use for this command. Can also use `AWS_PROFILE`. Will also check `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` environment variables if not using AWS CLI. |
| `--aws-region` or `-r` | No | The AWS region for the integration. Can use `AWS_DEFAULT_REGION` environment variable. Defaults to AWS session region. |
| `--aws-role-policy` | No | Specify an alternative IAM role policy ARN for this integration. |

#### Uninstall Integration

```bash
newrelic-lambda integrations uninstall
```

| Option | Required? | Description |
|--------|-----------|-------------|
| `--aws-profile` or `-p` | No | The AWS profile to use for this command. Can also use `AWS_PROFILE`. Will also check `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` environment variables if not using AWS CLI. |
| `--aws-region` or `-r` | No | The AWS region for the integration. Can use `AWS_DEFAULT_REGION` environment variable. Defaults to AWS session region. |

### AWS Lambda Layers

#### Install Layer

```bash
newrelic-lambda layers install \
    --function <name or arn> \
    --nr-account-id <new relic account id>
```

| Option | Required? | Description |
|--------|-----------|-------------|
| `--function` or `-f` | Yes | The AWS Lambda function name or ARN in which to add a layer. |
| `--nr-account-id` or `-a` | Yes | The [New Relic Account ID](https://docs.newrelic.com/docs/accounts/install-new-relic/account-setup/account-id) this function should use. Can also use the `NEW_RELIC_ACCOUNT_ID` environment variable. |
| `--layer-arn` or `-l` | No | Specify a specific layer version ARN to use. This is auto detected by default. |
| `--upgrade` or `-u` | No | Permit upgrade to the latest layer version for this region and runtime. |
| `--aws-profile` or `-p` | No | The AWS profile to use for this command. Can also use `AWS_PROFILE`. Will also check `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` environment variables if not using AWS CLI. |
| `--aws-region` or `-r` | No | The AWS region this function is located. Can use `AWS_DEFAULT_REGION` environment variable. Defaults to AWS session region. |

#### Uninstall Layer

```bash
newrelic-lambda layers uninstall --function <name or arn>
```

| Option | Required? | Description |
|--------|-----------|-------------|
| `--function` or `-f` | Yes | The AWS Lambda function name or ARN in which to remove a layer. |
| `--layer-arn` or `-l` | No | Specify a specific layer version ARN to remove. This is auto detected by default. |
| `--aws-profile` or `-p` | No | The AWS profile to use for this command. Can also use `AWS_PROFILE`. Will also check `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` environment variables if not using AWS CLI. |
| `--aws-region` or `-r` | No | The AWS region this function is located. Can use `AWS_DEFAULT_REGION` environment variable. Defaults to AWS session region. |

### AWS Lambda Functions

#### List Functions

```bash
newrelic-lambda functions list
```

List functions with layer installed:

```bash
newrelic-lambda functions list --filter installed
```

| Option | Required? | Description |
|--------|-----------|-------------|
| `--filter` or `-f` | No | Filter to be applied to list of functions. Options are `all`, `installed` and `not-installed`. Defaults to `all`. |
| `--aws-profile` or `-p` | No | The AWS profile to use for this command. Can also use `AWS_PROFILE`. Will also check `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` environment variables if not using AWS CLI. |
| `--aws-region` or `-r` | No | The AWS region to use for htis command. Can use `AWS_DEFAULT_REGION` environment variable. Defaults to AWS session region. |


### NewRelic Log Subscription

#### Install Log Subscription

```bash
newrelic-lambda subscriptions install \--function <name or arn>
```

| Option | Required? | Description |
|--------|-----------|-------------|
| `--function` or `-f` | Yes | The AWS Lambda function name or ARN in which to add a log subscription. |
| `--aws-profile` or `-p` | No | The AWS profile to use for this command. Can also use `AWS_PROFILE`. Will also check `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` environment variables if not using AWS CLI. |
| `--aws-region` or `-r` | No | The AWS region this function is located. Can use `AWS_DEFAULT_REGION` environment variable. Defaults to AWS session region. |

#### Uninstall Log Subscription

```bash
newrelic-lambda subscriptions uninstall --function <name or arn>
```

| Option | Required? | Description |
|--------|-----------|-------------|
| `--function` or `-f` | Yes | The AWS Lambda function name or ARN in which to remove a log subscription. |
| `--aws-profile` or `-p` | No | The AWS profile to use for this command. Can also use `AWS_PROFILE`. Will also check `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` environment variables if not using AWS CLI. |
| `--aws-region` or `-r` | No | The AWS region this function is located. Can use `AWS_DEFAULT_REGION` environment variable. Defaults to AWS session region. |


## Contributing

We welcome code contributions (in the form of pull requests) from our user community. Before submitting a pull request please review [these guidelines](CONTRIBUTING.md).

Following these helps us efficiently review and incorporate your contribution and avoid breaking your code with future changes to the agent.

## Code style

We use the [black](https://github.com/ambv/black) code formatter.

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
