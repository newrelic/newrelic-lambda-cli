# Installer for IOpipe

Applies the IOpipe layers to functions in your
AWS account. Uses credentials as configured
for the AWS CLI.

# Installation & configuration

On your system CLI:

```
pip3 install git+https://github.com/iopipe/iopipe-install.git
```

This tool assumes the AWS cli tool is configured correctly. Install and configure the AWS CLI as such:

```
pip3 install awscli --upgrade --user
```

Run the awscli configuration wizard:

```
aws configure
```

Refer to the [AWS CLI User Guide](https://docs.aws.amazon.com/cli/latest/userguide/cli-chap-welcome.html) for advanced configuration options and support for the aws cli tool.

# Installing IOpipe with `iopipe-install`

The easiest way to update a function is to update it with
the AWS Lambda API:

```
iopipe-install lambda install --function <name or arn> --token <IOPIPE_TOKEN>
```

The token may also be passed by the CLI's environment variable, `IOPIPE_TOKEN`.

If your Lambda has been deployed by Cloudformation, this method will cause stack drift.


# Troubleshooting

## Error: `botocore.exceptions.NoRegionError: You must specify a region.`

The AWS cli tool is not configured for a region. You may run `aws configure` or set the environment variable `AWS_DEFAULT_REGION` on the cli.

To set the env var on the cli:

`export AWS_DEFAULT_REGION=us-east-1`

## Error: `botocore.exceptions.NoCredentialsError: Unable to locate credentials`

The AWS cli tool is not configured for an AWS account. You may run `aws configure` to configure your AWS environment.

If you have multiple credential configurations in `$HOME/.aws/credentials`, but none is set as a default, you may specify a profile using `export AWS_PROFILE=<name>`.
