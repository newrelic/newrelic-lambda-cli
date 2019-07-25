# Lambda onboarding script

This Python 3 script allows you to link an AWS account to NR Cloud integrations and configure it for receiving Lambda monitoring data from agents.
This script relies in AWS CLI to perform some actions in your AWS account, so you will need to install and configure it with proper credentials (explained below).

## Requirements

* Python >= 3.6
* [AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/cli-chap-install.html).
* You also have to perform the [initial configuration](https://docs.aws.amazon.com/cli/latest/userguide/cli-chap-configure.html) of the AWS CLI to set the proper credentials and default region.
 
  **Note**: If you have multiple AWS profiles and you don't want to use the default while running this script, set the `AWS_DEFAULT_PROFILE` environment variable to the name of the required profile.
  
  Make sure this new profile is properly configured (including the default region).
  Example:

        export AWS_DEFAULT_PROFILE=my-other-profile



## Note on permissions

In order to use the script you will need to have enough permissions in your New Relic account and in you AWS account.
In your New Relic account your user will have to either be an `Admin` or an `User` with the `Infrastructure manager` role.

In your AWS account will need to have enough permissions to create IAM resources (Role and Policy) and Lambda functions. These resources will be created via Coudformation stacks, so you will need permissions to create those.

The full list of permissions required in AWS are:

    Resource: *
    Actions:
        "cloudformation:CreateChangeSet",
        "cloudformation:CreateStack",
        "cloudformation:DescribeStacks",
        "iam:AttachRolePolicy",
        "iam:CreateRole",
        "iam:GetRole",
        "iam:PassRole",
        "lambda:AddPermission",
        "lambda:CreateFunction",
        "lambda:GetFunction",
        "logs:DeleteSubscriptionFilter",
        "logs:DescribeSubscriptionFilters",
        "logs:PutSubscriptionFilter"
        "s3:GetObject"

    Resource: "arn:aws:serverlessrepo:us-east-1:463657938898:applications/NewRelic-log-ingestion"
    Actions:
        "serverlessrepo:CreateCloudFormationTemplate"
        "serverlessrepo:GetCloudFormationTemplate"

## Installation

1. Download [this zip file](https://github.com/newrelic/nr-lambda-onboarding/archive/master.zip) that contains all files of this repository:

    `curl -L -O https://github.com/newrelic/nr-lambda-onboarding/archive/master.zip`

2. Uncompress the zip file:

    `unzip master.zip`

3. Change to `nr-lambda-onboarding-master` directory:

    `cd nr-lambda-onboarding-master`

4. Add execution permission to `newrelic-cloud` script:

    `chmod +x newrelic-cloud`

## Enable Lambda integration

`usage: ./newrelic-cloud set-up-lambda-integration [args]`

This command will execute all the required steps necessary to fully enable Lambda monitoring in your New Relic account.
The steps are:

* Link your  AWS account in NR Cloud integrations.
* Enable AWS Lambda integration.
* Install NewRelic-log-ingestion Lambda function. This function sends monitoring data from you instrumented functions to New Relic. It also sends data from VPC FlowLogs and RDS enhanced monitoring.

### Arguments

* **--nr-account-id** *NR_ACCOUNT_ID* : Your New Relic account ID.
* **--aws-role-policy** : (Optional) Name of the policy assigned to the AWS role. Supply a name if you want to create the role with a restricted policy (only Lambda permissions). Omit the parameter to create the role with the AWS default [`ReadOnlyAccess` policy](https://docs.newrelic.com/docs/integrations/amazon-integrations/getting-started/integrations-managed-policies).
* **--linked-account-name** *LINKED_ACCOUNT_NAME* : Name of your AWS account that will appear in NR Cloud integrations. It is used to easily identify you account in NR.The cloud account will be created if it does not exist yet.
* **--nr-api-key** *NR_API_KEY* : Your New Relic API key. [Check the documentation](https://docs.newrelic.com/docs/apis/getting-started/intro-apis/understand-new-relic-api-keys#user-api-key) on how to obtain an user API key.
* **--nr-license-key** *NR_LICENSE_KEY* : Your New Relic license key. [Check the documentation](https://docs.newrelic.com/docs/accounts/install-new-relic/account-setup/license-key) on how to obtain a license key.
* **--regions** *REGIONS* : (Optional) List of regions where to install the New Relic log ingestion function. If no value is supplied it will fetch the list of regions from EC2 and use that as the list of regions.

**Example:**

    ./newrelic-cloud set-up-lambda-integration --nr-account-id "account_id" --linked-account-name "account_name" --aws-role-policy "NewRelicLambdaPolicy" --nr-api-key "api_key" --nr-license-key "license_key" --regions "region_1" "region_2"

## Enable Lambda log streaming

`usage: ./newrelic-cloud stream-lambda-logs [args]`

This command will execute all the required steps necessary to start sending Lambda agent data to New Relic.
It will create a log subscription filter for each of the given intrumented Lambdas to NewRelic-log-ingestion function, so agent data will be streamed to this function which will forward it to New Relic ingestion services.

### Arguments

* **--functions** *FUNCTIONS* : One of more function (names) to enable log streaming.
* **--regions** *REGIONS* : (Optional) List of regions where the script will try to setup the log streaming for the given functions. If no value is supplied it will fetch the list of regions from EC2 and use that as the list of regions.

**Example:**

    ./newrelic-cloud stream-lambda-logs --functions "my-function-1" "my-function-2" --regions "region_1" "region_2"

## Check Lambda setup status

`usage: ./newrelic-cloud check-lambda-setup-status [args]`

This command will perform a few simple checks of the basic requirements for having Lambda instrumentation working.
It will not check for required permissions either in AWS or New Relic.

### Arguments

* **--nr-account-id** *NR_ACCOUNT_ID* : Your New Relic account id.
* **--linked-account-name** *LINKED_ACCOUNT_NAME* : Name of your AWS account that appears in NR Cloud integrations you want to check.
* **--nr-api-key** *NR_API_KEY* : Your New Relic user API key. Check the documentation on how to obtain an API key.
* **--nr-license-key** *NR_LICENSE_KEY* : Your New Relic license key. Check the documentation on how to obtain an license key.
* **--functions** *FUNCTIONS* : List of (space-separated) function names to check.
* **--regions** *REGIONS* (Optional) List of (space-separated) regions where to perform the checks.

**Example:**

    ./newrelic-cloud check-lambda-setup-status --nr-account-id "account_id" --linked-account-name "account_name"  --nr-api-key "api_key" --nr-license-key "license_key" --functions "my-function-1" "my-function-2" --regions "region_1" "region_2"