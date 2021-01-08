[![Community Project header](https://github.com/newrelic/opensource-website/raw/master/src/images/categories/Community_Project.png)](https://opensource.newrelic.com/oss-category/#community-project)

# newrelic-lambda-cli [![Build Status](https://circleci.com/gh/newrelic/newrelic-lambda-cli.svg?style=svg)](https://circleci.com/gh/newrelic/newrelic-lambda-cli) [![Coverage](https://codecov.io/gh/newrelic/newrelic-lambda-cli/branch/master/graph/badge.svg?token=1Rl7h0O1JJ)](https://codecov.io/gh/newrelic/newrelic-lambda-cli)

A CLI to install the New Relic AWS Lambda integration and layers.

## Table of Contents

* **[Features](#features)**
* **[Runtimes Supported](#runtimes-supported)**
* **[Requirements](#requirements)**
* **[Recommendations](#recommendations)**
* **[Installation](#installation)**
* **[Usage](#usage)**
    * [AWS Lambda Integration](#aws-lambda-integration)
    * [AWS Lambda Layers](#aws-lambda-layers)
    * [AWS Lambda Functions](#aws-lambda-functions)
    * [NewRelic Log Subscription](#newRelic-log-subscription)
* **[Docker](#docker)**
* **[Contributing](#contributing)**
* **[Code Style](#code-style)**
* **[Running Tests](#running-tests)**
* **[Troubleshooting](#troubleshooting)**

## Features

* Installs the New Relic AWS Lambda integration onto your AWS account
* Installs and configures a New Relic AWS Lambda layer onto your AWS Lambda functions
* Automatically selects the correct New Relic layer for your function's runtime and region
* Wraps your AWS Lambda functions without requiring a code change
* Supports Go, Java, .NET, Node.js and Python AWS Lambda runtimes
* Easily uninstall the AWS Lambda layer with a single command

## Runtimes Supported

* dotnetcore3.1
* java8.al2
* java11
* nodejs10.x
* nodejs12.x
* provided
* provided.al2
* python2.7
* python3.6
* python3.7
* python3.8

**Note:** Automatic handler wrapping is only supported for Node.js and Python. For other runtimes,
manual function wrapping is required using the runtime specific New Relic agent.

## Requirements

* Python >= 3.3
* Retrieve your [New relic Account ID](https://docs.newrelic.com/docs/accounts/install-new-relic/account-setup/account-id) and [User API Key](https://docs.newrelic.com/docs/apis/get-started/intro-apis/types-new-relic-api-keys#user-api-key)

## Recommendations

* Install the [AWS CLI](https://github.com/aws/aws-cli) and configure your environment with `aws configure`

## Installation

```bash
pip3 install newrelic-lambda-cli
```

Or clone this repo and run:

```bash
python3 setup.py install
```

To update the CLI, run:

```
pip3 install --upgrade newrelic-lambda-cli
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
    --nr-api-key <api key>
```

| Option | Required? | Description |
|--------|-----------|-------------|
| `--nr-account-id` or `-a` | Yes | The [New Relic Account ID](https://docs.newrelic.com/docs/accounts/install-new-relic/account-setup/account-id) for this integration. Can also use the `NEW_RELIC_ACCOUNT_ID` environment variable. |
| `--nr-api-key` or `-k` | Yes | Your [New Relic User API Key](https://docs.newrelic.com/docs/apis/get-started/intro-apis/types-new-relic-api-keys#user-api-key). Can also use the `NEW_RELIC_API_KEY` environment variable. |
| `--linked-account-name` or `-l` | No | A label for the New Relic Linked Account. This is how this integration will appear in New Relic. Defaults to "New Relic Lambda Integration - <AWS Account ID>". |
| `--enable-logs` or `-e` | No | Enables forwarding logs to New Relic Logging. This is disabled by default. Make sure you run `newrelic-lambda subscriptions install --function ... --filter-pattern ""` afterwards. |
| `--memory-size` or `-m` | No | Memory size (in MiB) for the New Relic log ingestion function. Default to 128MB. |
| `--nr-region` | No | The New Relic region to use for the integration. Can use the `NEW_RELIC_REGION` environment variable. Can be either `eu` or `us`. Defaults to `us`. |
| `--timeout` or `-t` | No | Timeout (in seconds) for the New Relic log ingestion function. Defaults to 30 seconds. |
| `--role-name` | No | Role name for the ingestion function. If you prefer to create and manage an IAM role for the function to assume out of band, do so and specify that role's name here. This avoids needing CAPABILITY_IAM. |
| `--integration-arn` | No | Specify an existing AWS IAM role to use for the New Relic Lambda integration instead of creating one. |
| `--aws-profile` or `-p` | No | The AWS profile to use for this command. Can also use `AWS_PROFILE`. Will also check `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` environment variables if not using AWS CLI. |
| `--aws-region` or `-r` | No | The AWS region for the integration. Can use `AWS_DEFAULT_REGION` environment variable. Defaults to AWS session region. |
| `--aws-role-policy` | No | Specify an alternative IAM role policy ARN for this integration. |
| `--disable-license-key-secret` | No | Don't create a managed secret for your account's New Relic License Key |
| `--tag <key> <value>` | No | Sets tags on the CloudFormation Stacks this CLI creates. Can be used multiple times, example: `--tag key1 value1 --tag key2 value2`. |

#### Uninstall Integration

```bash
newrelic-lambda integrations uninstall
```

| Option | Required? | Description |
|--------|-----------|-------------|
| `--aws-profile` or `-p` | No | The AWS profile to use for this command. Can also use `AWS_PROFILE`. Will also check `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` environment variables if not using AWS CLI. |
| `--aws-region` or `-r` | No | The AWS region for the integration. Can use `AWS_DEFAULT_REGION` environment variable. Defaults to AWS session region. |
| `--force` or `-f` | No | Forces uninstall non-interactively |
| `--nr-account-id` or `-a` | No | The [New Relic Account ID](https://docs.newrelic.com/docs/accounts/install-new-relic/account-setup/account-id) for the integration. Only required if also uninstalling the New Relic AWS Lambda integration. Can also use the `NEW_RELIC_ACCOUNT_ID` environment variable. |

#### Update Integration

Updates the New Relic log ingestion function to the latest version. Existing ingestion function parameters will 
retain their values, unless you specify different values on the command line. By default, installs the license key
secret, if it is missing.

```bash
newrelic-lambda integrations update 
```

| Option | Required? | Description |
|--------|-----------|-------------|
| `--nr-account-id` or `-a` | No | The [New Relic Account ID](https://docs.newrelic.com/docs/accounts/install-new-relic/account-setup/account-id) for the integration. Only required if changing the account to which the logs are sent. Can also use the `NEW_RELIC_ACCOUNT_ID` environment variable. |
| `--nr-api-key` or `-k` | No | Your [New Relic User API Key](https://docs.newrelic.com/docs/apis/get-started/intro-apis/types-new-relic-api-keys#user-api-key). Can also use the `NEW_RELIC_API_KEY` environment variable. Only required if changing the account to which the logs are sent. |
| `--disable-logs` or `-d` | No | Disables forwarding logs to New Relic Logging. Make sure you run `newrelic-lambda subscriptions install --function ...` afterwards. |
| `--enable-logs` or `-e` | No | Enables forwarding logs to New Relic Logging. Make sure you run `newrelic-lambda subscriptions install --function ... --filter-pattern ""` afterwards. |
| `--memory-size` or `-m` | No | Memory size (in MiB) for the New Relic log ingestion function. |
| `--nr-region` | No | The New Relic region to use for the integration. Can use the `NEW_RELIC_REGION` environment variable. Can be either `eu` or `us`. Defaults to `us`. |
| `--timeout` or `-t` | No | Timeout (in seconds) for the New Relic log ingestion function. |
| `--role-name` | No | Role name for the ingestion function. If you prefer to create and manage an IAM role for the function to assume out of band, do so and specify that role's name here. This avoids needing CAPABILITY_IAM. |
| `--aws-profile` or `-p` | No | The AWS profile to use for this command. Can also use `AWS_PROFILE`. Will also check `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` environment variables if not using AWS CLI. |
| `--aws-region` or `-r` | No | The AWS region for the integration. Can use `AWS_DEFAULT_REGION` environment variable. Defaults to AWS session region. |
| `--disable-license-key-secret` | No | Disable automatic creation of the license key secret on update. The secret is not created if it exists. |
| `--tag <key> <value>` | No | Sets tags on the CloudFormation Stacks this CLI creates. Can be used multiple times, example: `--tag key1 value1 --tag key2 value2`. |

### AWS Lambda Layers

#### Install Layer

```bash
newrelic-lambda layers install \
    --function <name or arn> \
    --nr-account-id <new relic account id>
```

| Option | Required? | Description |
|--------|-----------|-------------|
| `--function` or `-f` | Yes | The AWS Lambda function name or ARN in which to add a layer. Can provide multiple `--function` arguments. Will also accept `all`, `installed` and `not-installed` similar to `newrelic-lambda functions list`. |
| `--nr-account-id` or `-a` | Yes | The [New Relic Account ID](https://docs.newrelic.com/docs/accounts/install-new-relic/account-setup/account-id) this function should use. Can also use the `NEW_RELIC_ACCOUNT_ID` environment variable. |
| `--exclude` or `-e` | No | A function name to exclude while installing layers. Can provide multiple `--exclude` arguments. Only checked when `all`, `installed` and `not-installed` are used. See `newrelic-lambda functions list` for function names. |
| `--layer-arn` or `-l` | No | Specify a specific layer version ARN to use. This is auto detected by default. |
| `--upgrade` or `-u` | No | Permit upgrade to the latest layer version for this region and runtime. |
| `--disable-extension` | No | Disable the [New Relic Lambda Extension](https://github.com/newrelic/newrelic-lambda-extension). |
| `--enable-extension-function-logs` | No | Enable forwarding logs via the [New Relic Lambda Extension](https://github.com/newrelic/newrelic-lambda-extension). Disabled by default. |
| `--aws-profile` or `-p` | No | The AWS profile to use for this command. Can also use `AWS_PROFILE`. Will also check `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` environment variables if not using AWS CLI. |
| `--aws-region` or `-r` | No | The AWS region this function is located. Can use `AWS_DEFAULT_REGION` environment variable. Defaults to AWS session region. |
| `--nr-api-key` or `-k` | No | Your [New Relic User API Key](https://docs.newrelic.com/docs/apis/get-started/intro-apis/types-new-relic-api-keys#user-api-key). Can also use the `NEW_RELIC_API_KEY` environment variable. Only used if `--enable-extension` is set and there is no New Relic license key in AWS Secrets Manager. |
| `--nr-region` | No | The New Relic region to use for the integration. Can use the `NEW_RELIC_REGION` environment variable. Can be either `eu` or `us`. Defaults to `us`. Only used if `--enable-extension` is set and there is no New Relic license key in AWS Secrets Manager. |

#### Uninstall Layer

```bash
newrelic-lambda layers uninstall --function <name or arn>
```

| Option | Required? | Description |
|--------|-----------|-------------|
| `--function` or `-f` | Yes | The AWS Lambda function name or ARN in which to remove a layer. Can provide multiple `--function` arguments. Will also accept `all`, `installed` and `not-installed` similar to `newrelic-lambda functions list`. |
| `--exclude` or `-e` | No | A function name to exclude while uninstalling layers. Can provide multiple `--exclude` arguments. Only checked when `all`, `installed` and `not-installed` are used. See `newrelic-lambda functions list` for function names. |
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
| `--output` or `-o` | No | Specify the desired output format. Supports `table` and `text`. Defaults to `table`. |
| `--aws-profile` or `-p` | No | The AWS profile to use for this command. Can also use `AWS_PROFILE`. Will also check `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` environment variables if not using AWS CLI. |
| `--aws-region` or `-r` | No | The AWS region to use for this command. Can use `AWS_DEFAULT_REGION` environment variable. Defaults to AWS session region. |

### NewRelic Log Subscription

#### Install Log Subscription

```bash
newrelic-lambda subscriptions install --function <name or arn>
```

| Option | Required? | Description |
|--------|-----------|-------------|
| `--function` or `-f` | Yes | The AWS Lambda function name or ARN in which to add a log subscription. Can provide multiple `--function` arguments. Will also accept `all`, `installed` and `not-installed` similar to `newrelic-lambda functions list`. |
| `--exclude` or `-e` | No | A function name to exclude while installing subscriptions. Can provide multiple `--exclude` arguments. Only checked when `all`, `installed` and `not-installed` are used. See `newrelic-lambda functions list` for function names. |
| `--filter-pattern` | No | Specify a custom log subscription filter pattern. To collect all logs use `--filter-pattern ""`. | 
| `--aws-profile` or `-p` | No | The AWS profile to use for this command. Can also use `AWS_PROFILE`. Will also check `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` environment variables if not using AWS CLI. |
| `--aws-region` or `-r` | No | The AWS region this function is located. Can use `AWS_DEFAULT_REGION` environment variable. Defaults to AWS session region. |

#### Uninstall Log Subscription

```bash
newrelic-lambda subscriptions uninstall --function <name or arn>
```

| Option | Required? | Description |
|--------|-----------|-------------|
| `--function` or `-f` | Yes | The AWS Lambda function name or ARN in which to remove a log subscription. Can provide multiple `--function` arguments. Will also accept `all`, `installed` and `not-installed` similar to `newrelic-lambda functions list`. |
| `--exclude` or `-e` | No | A function name to exclude while uninstalling subscriptions. Can provide multiple `--exclude` arguments. Only checked when `all`, `installed` and `not-installed` are used. See `newrelic-lambda functions list` for function names. |
| `--aws-profile` or `-p` | No | The AWS profile to use for this command. Can also use `AWS_PROFILE`. Will also check `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` environment variables if not using AWS CLI. |
| `--aws-region` or `-r` | No | The AWS region this function is located. Can use `AWS_DEFAULT_REGION` environment variable. Defaults to AWS session region. |

## Docker

Now, you can run newrelic-lambda-cli as a container.

```bash
docker build -t newrelic-lambda-cli .
docker run -e AWS_PROFILE=your_profile -v $HOME/.aws:/home/newrelic-lambda-cli/.aws newrelic-lambda-cli functions list
```

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

## Troubleshooting

**Upgrade the CLI**: A good first step, as we push updates frequently.

```
pip3 install --upgrade newrelic-lambda-cli
```

**UnrecognizedClientException**:
>`(UnrecognizedClientException) when calling the GetFunction operation: The security token included in the request is invalid.`

If you see this error, it means that specifying the region is necessary, and you need to supply the `--aws-region` flag to your command.

**Unable to locate credentials:**
>`Function: None, Region: None, Error: Failed to set up lambda integration: 'Unable to locate credentials. You can configure credentials by running "aws configure".'`

1. The AWS profile may not be properly configured; review documentation to [Configure your AWS Profile](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-files.html) (make sure the default region is set!).
2. If there are multiple AWS profiles and the correct one is not specified, you can run `export AWS_DEFAULT_PROFILE=MY_OTHER_PROFILE` to set the environment variable to the proper profile.

**SimulatePrincipalPolicy**:
>`botocore.errorfactory.InvalidInputException: An error occurred (InvalidInput) when calling the SimulatePrincipalPolicy operation: Invalid Entity Arn: arn:aws:sts::123456789012:assumed-role/u-admin/botocore-session-0987654321 does not clearly define entity type and name.`

Some AWS accounts can have permission to operate on resources without having access to SimulatePrincipalPolicy.
If this is the case, supply the `--no-aws-permissions-check` flag to your command.

**Error adding new region to integration**:
>`Linking New Relic account to AWS account
Traceback (most recent call last):
  ...
  File "/Users/USER/PYTHONPATH/lib/python3.8/site-packages/newrelic_lambda_cli/gql.py", line 131, in link_account
    return res["cloudLinkAccount"]["linkedAccounts"][0]  
IndexError: list index out of range`

This error can happen if you have an existing AWS integration, and are running `newrelic-lambda integrations install` with a different `--linked-account-name` (for instance, to add a new region to the integration). The linked account name can be whatever you want it to be, but needs to be consistent with the previously linked AWS account.

**AWS Secrets Manager Secret Name Conflict**
This CLI manages a AWS Secrets Manager secret with the name `NEW_RELIC_LICENSE_KEY`. If
you run into a CloudFormation error reporting that this secret already exists, make
sure that you delete any existing secrets and try again. Keep in mind, by default in the
AWS console when you delete a secret from AWS Secrets Manager that it will not delete
the secret permnantly for several days. You will need to perform a "force delete without
recovery" when deleting the secret to avoid this naming conflict.
