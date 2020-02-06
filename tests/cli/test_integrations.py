import boto3
from moto import mock_cloudformation, mock_iam

from newrelic_lambda_cli.cli import cli, register_groups
from newrelic_lambda_cli.integrations import (
    create_integration_role,
    create_log_ingestion_function,
)


@mock_cloudformation
@mock_iam
def test_integrations_uninstall(aws_credentials, cli_runner):
    """
    Assert that 'newrelic-lambda integrations uninstall' uninstall the log ingestion
    function/role if present
    """
    register_groups(cli)
    result = cli_runner.invoke(
        cli,
        [
            "integrations",
            "uninstall",
            "--no-aws-permissions-check",
            "--nr-account-id",
            "12345678",
        ],
        env={"AWS_DEFAULT_REGION": "us-east-1"},
        input="y\ny",
    )

    assert result.exit_code == 0
    assert result.stdout == (
        "This will uninstall the New Relic AWS Lambda integration role. Are you sure you want to proceed? [y/N]: y\n"  # noqa
        "No New Relic AWS Lambda Integration found, skipping\n"
        "This will uninstall the New Relic AWS Lambda log ingestion function and role. Are you sure you want to proceed? [y/N]: y\n"  # noqa
        "No New Relic AWS Lambda log ingestion found in region us-east-1, skipping\n"
        "✨ Uninstall Complete ✨\n"
    )

    session = boto3.Session(region_name="us-east-1")
    create_integration_role(session, None, 12345678)
    create_log_ingestion_function(session, "mock-nr-license-key")

    result2 = cli_runner.invoke(
        cli,
        [
            "integrations",
            "uninstall",
            "--no-aws-permissions-check",
            "--nr-account-id",
            "12345678",
        ],
        env={"AWS_DEFAULT_REGION": "us-east-1"},
        input="y\ny",
    )

    assert result2.exit_code == 0
    assert result2.stdout == (
        "This will uninstall the New Relic AWS Lambda integration role. Are you sure you want to proceed? [y/N]: y\n"  # noqa
        "Deleting New Relic AWS Lambda Integration stack 'NewRelicLambdaIntegrationRole-12345678'\n"  # noqa
        "Waiting for stack deletion to complete, this may take a minute... ✔️ Done\n"
        "This will uninstall the New Relic AWS Lambda log ingestion function and role. Are you sure you want to proceed? [y/N]: y\n"  # noqa
        "Deleting New Relic log ingestion stack 'NewRelicLogIngestion'\n"
        "Waiting for stack deletion to complete, this may take a minute... ✔️ Done\n"
        "✨ Uninstall Complete ✨\n"
    )


@mock_cloudformation
@mock_iam
def test_integrations_uninstall_force(cli_runner):
    """
    Assert that 'newrelic-lambda integrations uninstall --force' uninstalls the log
    ingestion function/role without prompting if present
    """
    register_groups(cli)
    result = cli_runner.invoke(
        cli,
        [
            "integrations",
            "uninstall",
            "--no-aws-permissions-check",
            "--nr-account-id",
            "12345678",
            "--force",
        ],
        env={"AWS_DEFAULT_REGION": "us-east-1"},
    )

    assert result.exit_code == 0
    assert result.stdout == (
        "No New Relic AWS Lambda Integration found, skipping\n"
        "No New Relic AWS Lambda log ingestion found in region us-east-1, skipping\n"
        "✨ Uninstall Complete ✨\n"
    )

    session = boto3.Session(region_name="us-east-1")
    create_integration_role(session, None, 12345678)
    create_log_ingestion_function(session, "mock-nr-license-key")

    result2 = cli_runner.invoke(
        cli,
        [
            "integrations",
            "uninstall",
            "--no-aws-permissions-check",
            "--nr-account-id",
            "12345678",
            "--force",
        ],
        env={"AWS_DEFAULT_REGION": "us-east-1"},
    )

    assert result2.exit_code == 0
    assert result2.stdout == (
        "Deleting New Relic AWS Lambda Integration stack 'NewRelicLambdaIntegrationRole-12345678'\n"  # noqa
        "Waiting for stack deletion to complete, this may take a minute... ✔️ Done\n"
        "Deleting New Relic log ingestion stack 'NewRelicLogIngestion'\n"
        "Waiting for stack deletion to complete, this may take a minute... ✔️ Done\n"
        "✨ Uninstall Complete ✨\n"
    )
