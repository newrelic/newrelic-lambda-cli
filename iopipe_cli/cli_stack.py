from . import stack
from . import utils

import click
import os


IOPIPE_FF_CLOUDFORMATION = os.environ.get('IOPIPE_FF_CLOUDFORMATION')


@click.group(name="stack")
def stack_group():
    None

def register(group):
    if not IOPIPE_FF_CLOUDFORMATION:
        return

    group.add_command(stack_group)
    stack_group.add_command(stack_template)
    stack_group.add_command(stack_install)

@click.command(name="template")
@click.option("--input", "-i", default='template.json', help="Cloudformation JSON file.")
@click.option("--function", "-f", required=True, metavar="<arn>", help="Lambda function name or ARN")
@click.option("--output", "-o", default='-', help="Output file for modified template.")
@click.option("--token", "-t", envvar="IOPIPE_TOKEN", required=True, metavar="<token>", help="IOpipe Token", callback=utils.check_token)
def stack_template(template, function, output, token):
    stack.update_cloudformation_file(template, function, output, token)

@click.command(name="list")
def stack_list(stack_id, function, token):
    click.echo_via_pager(stack.get_stack_ids())

@click.command(name="install")
@click.option("--stack-id", "-s", required=True, help="Cloudformation Stack ID.")
@click.option("--function", "-f", required=True, metavar="<arn>", help="Lambda function name or ARN")
@click.option("--token", "-t", envvar="IOPIPE_TOKEN", required=True, metavar="<token>", help="IOpipe Token", callback=utils.check_token)
def stack_install(stack_id, function, token):
    stack.update_cloudformation_stack(stack_id, function, token)
