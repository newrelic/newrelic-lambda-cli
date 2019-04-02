#!/usr/bin/env python3
from . import update

import boto3
import botocore
import click
import itertools
import json
import jwt
import os
import shutil

IOPIPE_FF_CLOUDFORMATION = os.environ.get('IOPIPE_FF_CLOUDFORMATION')

def all_lambda_regions():
    return boto3.session.Session().get_available_regions('lambda')

def check_token(ctx, param, value):
    try:
        jwt.decode(value, verify=False)
        return value 
    except:
        raise click.BadParameter('token invalid.')

@click.command(name="template")
@click.option("--input", "-i", default='template.json', help="Cloudformation JSON file.")
@click.option("--function", "-f", required=True, metavar="<arn>", help="Lambda function name or ARN")
@click.option("--output", "-o", default='-', help="Output file for modified template.")
@click.option("--token", "-t", envvar="IOPIPE_TOKEN", required=True, metavar="<token>", help="IOpipe Token", callback=check_token)
def cf_update_template(template, function, output, token):
    update.update_cloudformation_file(template, function, output, token)

@click.command(name="update")
@click.option("--stack-id", "-s", required=True, help="Cloudformation Stack ID.")
@click.option("--function", "-f", required=True, metavar="<arn>", help="Lambda function name or ARN")
@click.option("--token", "-t", envvar="IOPIPE_TOKEN", required=True, metavar="<token>", help="IOpipe Token", callback=check_token)
def cf_update_stack(stack_id, function, token):
    update.update_cloudformation_stack(stack_id, function, token)

@click.command(name="install")
@click.option("--region", "-r", help="AWS region", type=click.Choice(all_lambda_regions()))
@click.option("--function", "-f", required=True, metavar="<arn>", help="Lambda function name or ARN")
@click.option("--layer-arn", "-l", metavar="<arn>", help="Layer ARN for IOpipe library (default: auto-detect)")
@click.option("--verbose", "-v", help="Print new function configuration upon completion.", is_flag=True)
@click.option("--java-type", "-j", help="Specify Java handler type, required for Java functions.", type=click.Choice(['request', 'stream']))
@click.option("--token", "-t", envvar="IOPIPE_TOKEN", required=True, metavar="<token>", help="IOpipe Token", callback=check_token)
def api_install(region, function, layer_arn, verbose, token, java_type):
    try:
        resp = update.apply_function_api(region, function, layer_arn, token, java_type)
        if not resp:
            click.echo("\nInstallation failed.")
            return
        if verbose:
            click.echo(json.dumps(resp, indent=2))
        click.echo("\nInstall complete.")
    except update.MultipleLayersException:
        print("Multiple layers found. Pass --layer-arn to specify layer ARN")
    except update.UpdateLambdaException as e:
        print(e);
    except boto3.exceptions.Boto3Error:
        print("Error in communication to AWS. Check aws-cli configuration.")

@click.command(name="uninstall")
@click.option("--region", "-r", help="AWS region", type=click.Choice(all_lambda_regions()))
@click.option("--function", "-f", required=True, metavar="<arn>", help="Lambda function name or ARN")
@click.option("--layer-arn", "-l", metavar="<arn>", help="Layer ARN for IOpipe library (default: auto-detect)")
@click.option("--verbose", "-v", help="Print new function configuration upon completion.", is_flag=True)
def api_uninstall(region, function, layer_arn, verbose):
    try:
        resp = update.remove_function_api(region, function, layer_arn)
        if not resp:
            click.echo("\nRemoval failed.")
            return
        if verbose:
            click.echo(json.dumps(resp, indent=2))
        click.echo("\nRemoval of IOpipe layers and configuration complete.")
    except boto3.exceptions.Boto3Error:
        print ("Error in communication to AWS. Check aws-cli configuration.")

@click.command(name="list")
@click.option("--region", "-r", help="AWS region", type=click.Choice(all_lambda_regions()))
@click.option("--quiet", "-q", help="Skip headers", is_flag=True)
@click.option("--filter", "-f", help="Apply a filter to the list.", type=click.Choice(['all', 'installed', 'not-installed']))
def lambda_list_functions(region, quiet, filter):
    # this use of `filter` worries me as it's a keyword,
    # but it actually works? Clickly doesn't give
    # us enough control here to change the variable name? -Erica
    buffer = []
    _, consrows = shutil.get_terminal_size((80,50))
    functions_iter = update.list_functions(region, quiet, filter)
    for idx, line in enumerate(functions_iter):
        buffer.append(line)

        # This is designed to ONLY page when there's
        # more rows than the height of the console.
        # If we've buffered as many lines as the height of the console,
        # then start a pager and empty the buffer.
        if idx > 0 and idx % consrows == 0:
            click.echo_via_pager(itertools.chain(iter(buffer), functions_iter))
            buffer = []
            break
    # Print all lines for non-paged results.
    for line in buffer:
        click.echo(line, nl=False)

@click.group()
def cli():
    None

@click.group()
def stack():
    None

@click.group(name="lambda")
def lambda_group():
    None

#@click.group()
#def sam():
#    None
#cli.add_command(sam)
#
#@click.group()
#def gosls():
#    None
#cli.add_command(gosls)

def click_groups():
    if IOPIPE_FF_CLOUDFORMATION:
        cli.add_command(stack)
        stack.add_command(cf_update_template)
        stack.add_command(cf_update_stack)

    cli.add_command(lambda_group)
    lambda_group.add_command(lambda_list_functions)
    lambda_group.add_command(api_install)
    lambda_group.add_command(api_uninstall)

def main():
    click_groups()
    try:
        cli()
    except botocore.exceptions.NoRegionError:
        print("You must specify a region. Pass `--region` or run `aws configure`.")
    except botocore.exceptions.NoCredentialsError:
        print("No AWS credentials configured. Did you run `aws configure`?")
