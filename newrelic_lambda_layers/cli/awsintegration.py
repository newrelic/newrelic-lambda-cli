import boto3
import click

from .. import permissions
from .decorators import add_options, AWS_OPTIONS


@click.group(name="integration")
def integration_group():
    """Manage New Relic AWS Integrations"""
    pass


def register(group):
    group.add_command(integration_group)
    integration_group.add_command(integration_install)


@click.command(name="install")
@add_options(AWS_OPTIONS)
def integration_install(aws_profile, aws_region):
    """Install New Relic AWS Integration"""
    session = boto3.Session(profile_name=aws_profile, region_name=aws_region)
    permissions.ensure_setup_permissions(session)
    click.echo("Install the integration here")
