# Lambda onboarding script

This Python 3 script allows you to link an AWS account to NR Cloud integrations and configure it for receiving Lambda monitoring data from agents.
This script relies in AWS CLI to perform some actions in your AWS account, so you will need to install and configure it with proper credentials (explained below).

## Requirements

* **Python >= 2.6.6** (including [pip](https://pip.pypa.io/en/stable/installing/), if it is not already installed)  
	**_Note_**:  This doc assumes that you have Python2 in your path, but you can force `newrelic-cloud` to use Python3 by prefixing the command with `python3`. If you haven't added your Python bin directory to your path yet, you will need to do so. For example, with the default Python (2.7) on MacOS Mojave, you would need to add `~/Library/Python/2.7/bin` to your path. 
* **[AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/cli-chap-install.html)**  
* You also have to perform the [initial configuration](https://docs.aws.amazon.com/cli/latest/userguide/cli-chap-configure.html) of the AWS CLI to set the proper credentials and default region.

  ```
  $ aws configure
  AWS Access Key ID [None]: AKIAIOSFODNN7EXAMPLE
  AWS Secret Access Key [None]: wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
  Default region name [None]: us-west-2
  Default output format [None]: json
  ```  

  **_Note_**: If you have multiple AWS profiles and you don't want to use the default while running this script, set the `AWS_DEFAULT_PROFILE` environment variable to the name of the required profile.
  
  Make sure this new profile is properly configured (including the default region).
  Example:

        export AWS_DEFAULT_PROFILE=my-other-profile


## Note on permissions

In order to use the script you will need to have enough permissions in your New Relic account and in your AWS account.
In your New Relic account, your user will have to either be an `Admin` or an `User` with the `Infrastructure manager` role.

In your AWS account, you will need to have enough permissions to create IAM resources (Role and Policy) and Lambda functions. These resources will be created via CoudFormation stacks, so you will need permissions to create those.

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

**Python2 usage:** `./newrelic-cloud set-up-lambda-integration [args]`   
**Python3 usage:** `python3 ./newrelic-cloud set-up-lambda-integration [args]`

This command will execute all the required steps necessary to fully enable Lambda monitoring in your New Relic account.
The steps are:

* Link your  AWS account in NR Cloud integrations.
* Enable AWS Lambda integration.
* Install NewRelic-log-ingestion Lambda function. This function sends monitoring data from you instrumented functions to New Relic. It also sends data from VPC FlowLogs and RDS enhanced monitoring.

### Arguments

* **--nr-account-id** *NR_ACCOUNT_ID* : Your New Relic account ID.
* **--aws-role-policy** : (Optional) Name of the policy assigned to the AWS role. Supply a name if you want to create the role with a restricted policy (only Lambda permissions). Omit the parameter to create the role with the AWS default [`ReadOnlyAccess` policy](https://docs.newrelic.com/docs/integrations/amazon-integrations/getting-started/integrations-managed-policies).
* **--linked-account-name** *LINKED_ACCOUNT_NAME* : Name of your AWS account that will appear in NR Cloud integrations. It is used to easily identify your account in NR. The cloud account will be created if it does not exist yet.
* **--nr-api-key** *NR_API_KEY* : Your New Relic User API key (different from New Relic REST API key!). [Check the documentation](https://docs.newrelic.com/docs/apis/getting-started/intro-apis/understand-new-relic-api-keys#user-api-key) on how to obtain a user API key.
* **--regions** *REGIONS* : (Optional) List of regions where to install the New Relic log ingestion function. If no value is supplied it will fetch the list of regions from EC2 and use that as the list of regions.
* **--nr-region** *NR_REGION* : (Optional) Set to "eu" if you're integrating with the New Relic EU region. Defaults to US. 

**_Note_**: if this command fails with the error `(UnrecognizedClientException) when calling the GetFunction operation: The security token included in the request is invalid.`, it is commonly because there was no region supplied. Just add the --regions flag with your authorized regions,  then run the command again and it should pass.

**Example:**

```
./newrelic-cloud set-up-lambda-integration \
    --nr-account-id "account_id" \
    --linked-account-name "account_name" \
    --aws-role-policy "NewRelicLambdaPolicy" \
    --nr-api-key "api_key" \
    --regions "region_1" "region-2"
```

## Enable Lambda log streaming

**Python2 usage:** `./newrelic-cloud stream-lambda-logs [args]`  
**Python3 usage:** `python3 ./newrelic-cloud stream-lambda-logs [args]`

This command will execute all the required steps necessary to start sending Lambda agent data to New Relic.
It will create a log subscription filter for each of the given intrumented Lambdas to NewRelic-log-ingestion function, so agent data will be streamed to this function which will forward it to New Relic ingestion services.

### Arguments

* **--functions** *FUNCTIONS* : One of more function (names) to enable log streaming.
* **--regions** *REGIONS* : (Optional) List of regions where the script will try to setup the log streaming for the given functions. If no value is supplied it will fetch the list of regions from EC2 and use that as the list of regions.

**Example:**

    ./newrelic-cloud stream-lambda-logs --functions "my-function-1" "my-function-2" --regions "region_1" "region_2"

## Check Lambda setup status

**Python2 usage:** `./newrelic-cloud check-lambda-setup-status [args]`  
**Python3 usage:** `python3 ./newrelic-cloud check-lambda-setup-status [args]`

This command will perform a few simple checks of the basic requirements for having Lambda instrumentation working.
It will not check for required permissions either in AWS or New Relic.

### Arguments

* **--nr-account-id** *NR_ACCOUNT_ID* : Your New Relic account id.
* **--linked-account-name** *LINKED_ACCOUNT_NAME* : Name of your AWS account that appears in NR Cloud integrations you want to check.
* **--nr-api-key** *NR_API_KEY* : Your New Relic user API key. Check the documentation on how to obtain an API key.
* **--nr-region** *NR_REGION* : (Optional) Set to "eu" if you're integrating with the New Relic EU region. Defaults to US. 
* **--functions** *FUNCTIONS* : List of (space-separated) function names to check.
* **--regions** *REGIONS* (Optional) List of (space-separated) regions where to perform the checks.

**Example:**

```
./newrelic-cloud check-lambda-setup-status \
--nr-account-id "account_id" \
--linked-account-name "account_name" \
--nr-api-key "api_key" \
--functions "my-function-1" "my-function-2" \
--regions "region_1" "region_2"
```  

## Troubleshooting

**AWS Credentials error:**
>Function: None, Region: None, Error: Failed to set up lambda integration: 'Unable to locate credentials. You can configure credentials by running "aws configure".'

There are a couple of potential solutions here:

1. The AWS profile may not be properly configured; review documentation to [Configure your AWS Profile](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-files.html) (make sure the default region is set!).
2. If there are multiple AWS profiles and the correct one is not specified, you can run `export AWS_DEFAULT_PROFILE=MY_OTHER_PROFILE` to set the environment variable to the proper profile.

**Python3 certificate error:**  
>`Failed to set up lambda integration: <urlopen error [SSL: CERTIFICATE_VERIFY_FAILED]` 
>`certificate verify failed: unable to get local issuer certificate (_ssl.c:1056)>`

Solution: install Certifi and run the certificate installation command (make sure to change the second command to reflect your Python version!):

```
pip install certifi 
/Applications/Python\ 3.7/Install\ Certificates.command
```

**AWS Console "Module Import" error:**
>Unable to Import Module 'index' Error

This happens on file upload when users zip a directory containing files, instead of selecting the files within the directory and zipping them for upload: [Zipping files for AWS](https://docs.aws.amazon.com/elasticbeanstalk/latest/dg/applications-sourcebundle.html#using-features.deployment.source.gui)

**AWS Log Ingestion UI error:**
This is a common UI bug that does not affect anything and can be safely ignored.
![](https://drive.google.com/uc?id=1soeSfMiFT068_K6dhxa649UtKlY30qGQ)

**AWS CLI output error**
>Failed actions:
  Function: None, Region: None, Error: Failed to set up lambda integration: Extra data: line 1 column 14 (char 13)
  
This was an error that happened in earlier versions of the script if users did not specify JSON format for AWS CLI output; JSON output is now forced by the script, so make sure you are using the most recent version of the script.

**404 Error (usually an older script version):**  
Solution: ensure you are using the most recent version of the onboarding script.