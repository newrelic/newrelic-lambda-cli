#!/usr/bin/env python3
from . import awslambda
from . import stack 

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
    if not hasattr(jwt, 'PyJWT'):
        raise Exception("Incompatible `jwt` library detected. Must have `pyjwt` installed.")
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
def stack_template(template, function, output, token):
    stack.update_cloudformation_file(template, function, output, token)

@click.command(name="list")
def stack_list(stack_id, function, token):
    click.echo_via_pager(stack.get_stack_ids())

@click.command(name="install")
@click.option("--stack-id", "-s", required=True, help="Cloudformation Stack ID.")
@click.option("--function", "-f", required=True, metavar="<arn>", help="Lambda function name or ARN")
@click.option("--token", "-t", envvar="IOPIPE_TOKEN", required=True, metavar="<token>", help="IOpipe Token", callback=check_token)
def stack_install(stack_id, function, token):
    stack.update_cloudformation_stack(stack_id, function, token)

@click.command(name="install")
@click.option("--region", "-r", help="AWS region", type=click.Choice(all_lambda_regions()))
@click.option("--function", "-f", required=True, metavar="<arn>", help="Lambda function name or ARN")
@click.option("--layer-arn", "-l", metavar="<arn>", help="Layer ARN for IOpipe library (default: auto-detect)")
@click.option("--verbose", "-v", help="Print new function configuration upon completion.", is_flag=True)
@click.option("--java-type", "-j", help="Specify Java handler type, required for Java functions.", type=click.Choice(['request', 'stream']))
@click.option("--token", "-t", envvar="IOPIPE_TOKEN", required=True, metavar="<token>", help="IOpipe Token", callback=check_token)
def lambda_install(region, function, layer_arn, verbose, token, java_type):
    resp = awslambda.apply_function_api(region, function, layer_arn, token, java_type)
    if not resp:
        click.echo("\nInstallation failed.")
        return
    if verbose:
        click.echo(json.dumps(resp, indent=2))
    click.echo("\nInstall complete.")

@click.command(name="uninstall")
@click.option("--region", "-r", help="AWS region", type=click.Choice(all_lambda_regions()))
@click.option("--function", "-f", required=True, metavar="<arn>", help="Lambda function name or ARN")
@click.option("--layer-arn", "-l", metavar="<arn>", help="Layer ARN for IOpipe library (default: auto-detect)")
@click.option("--verbose", "-v", help="Print new function configuration upon completion.", is_flag=True)
def lambda_uninstall(region, function, layer_arn, verbose):
    resp = awslambda.remove_function_api(region, function, layer_arn)
    if not resp:
        click.echo("\nRemoval failed.")
        return
    if verbose:
        click.echo(json.dumps(resp, indent=2))
    click.echo("\nRemoval of IOpipe layers and configuration complete.")

@click.command(name="list")
@click.option("--region", "-r", help="AWS region", type=click.Choice(all_lambda_regions()))
@click.option("--quiet", "-q", help="Skip headers", is_flag=True)
@click.option("--filter", "-f", help="Apply a filter to the list.", type=click.Choice(['all', 'installed', 'not-installed']))
def lambda_list_functions(region, quiet, filter):
    # this use of `filter` worries me as it's a keyword,
    # but it actually works? Clickly doesn't give
    # us enough control here to change the variable name? -Erica
    coltmpl = "{:<64}\t{:<12}\t{:>12}\n"
    conscols, consrows = shutil.get_terminal_size((80,50))

    def _header():
        if not quiet:
            yield coltmpl.format("Function Name", "Runtime", "Installed")
            # ascii table limbo line ---
            yield ("{:-^%s}\n" % (str(conscols),)).format("")

    def _format(funcs):
        for f in funcs:
            yield coltmpl.format(f.get("FunctionName"), f.get("Runtime"), f.get("-x-iopipe-enabled", False))

    buffer = []
    functions_iter = awslambda.list_functions(region, quiet, filter)
    for idx, line in enumerate(itertools.chain(_header(), _format(functions_iter))):
        buffer.append(line)

        # This is designed to ONLY page when there's
        # more rows than the height of the console.
        # If we've buffered as many lines as the height of the console,
        # then start a pager and empty the buffer.
        if idx > 0 and idx % consrows == 0:
            click.echo_via_pager(itertools.chain(iter(buffer), _format(functions_iter)))
            buffer = []
            break
    # Print all lines for non-paged results.
    for line in iter(buffer):
        click.echo(line, nl=False)

@click.group(name="cli")
def cli_group():
    None

@click.group(name="stack")
def stack_group():
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
        cli_group.add_command(stack)
        stack_group.add_command(stack_template)
        stack_group.add_command(stack_install)

    cli_group.add_command(lambda_group)
    lambda_group.add_command(lambda_list_functions)
    lambda_group.add_command(lambda_install)
    lambda_group.add_command(lambda_uninstall)

def main():
    click_groups()
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

