#!/usr/bin/env python3
from . import awslambda
from . import cli_awslambda
from . import cli_stack
from . import utils

import boto3
import botocore
import click
import itertools
import json
import jwt
import os
import shutil


@click.group(name="cli")
def cli_group():
    None

def click_groups(group):
    cli_awslambda.register(group)
    cli_stack.register(group)

def main():
    click_groups(cli_group)
    try:
        cli_group()
    except botocore.exceptions.NoRegionError:
        print("You must specify a region. Pass `--region` or run `aws configure`.")
    except botocore.exceptions.NoCredentialsError:
        print("No AWS credentials configured. Did you run `aws configure`?")
    except awslambda.MultipleLayersException:
        print("Multiple layers found. Pass --layer-arn to specify layer ARN")
    except awslambda.UpdateLambdaException as e:
        print(e)
    except boto3.exceptions.Boto3Error:
        print("Error in communication to AWS. Check aws-cli configuration.")
