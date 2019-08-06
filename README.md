# Installer for IOpipe

Applies the IOpipe layers to functions in your
AWS account. Uses credentials as configured
for the AWS CLI.

## Runtimes supported
- Node10.x
- Java8.x
- Python2.7
- Python3.6

# Installation & configuration

On your system CLI:

```
pip3 install iopipe-cli
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

# Installing IOpipe for functions with `iopipe`

The easiest way to update a function is to update it with
the AWS Lambda API:

```
iopipe lambda install --function <name or arn> --token <IOPIPE_TOKEN>
```

The token may also be passed by the CLI's environment variable, `IOPIPE_TOKEN`.

If your Lambda has been deployed by Cloudformation, this method will cause stack drift.


# Troubleshooting

## MacOS X: cannot find `iopipe` after installation

Make sure your python script bin directory is included in your path.

The [documentation for the AWS cli](https://docs.aws.amazon.com/cli/latest/userguide/install-macos.html#awscli-install-osx-path) covers
this topic and describes a solution.

## Error: Invalid value for "--token" / "-t": token invalid.

Your token may be malformed or corrupted. Try copying-and-pasting again, or using quotations on the cli.

Some users also report that they have the incorrect `jwt` library installed on their system. This project
uses the popular `pyjwt` module installable from PyPi.

## Error: `Unknown parameter in input: "Layers", must be one of: FunctionName, Role, Handler, Description, Timeout, MemorySize, VpcConfig, Environment, Runtime, DeadLetterConfig, KMSKeyArn, TracingConfig, RevisionId`

If you encounter this error, please update your boto3 dependency to the latest version.
