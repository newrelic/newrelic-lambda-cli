import boto3
from moto import mock_cloudformation

from newrelic_lambda_cli.cli import cli, register_groups
from newrelic_lambda_cli.integrations import create_log_ingestion_function


@mock_cloudformation
def test_integrations_uninstall(cli_runner):
    """
    Assert that 'newrelic-lambda integrations uninstall' uninstall the log ingestion
    function/role if present
    """
    register_groups(cli)
    result = cli_runner.invoke(
        cli,
        ["integrations", "uninstall", "--no-aws-permissions-check"],
        env={"AWS_DEFAULT_REGION": "us-east-1"},
        input="y",
    )

    assert result.exit_code == 0
    assert result.stdout == (
        "This will uninstall the New Relic AWS Lambda log ingestion. Are you sure you want to proceed? [y/N]: y\n"  # noqa
        "No New Relic AWS Lambda log ingestion found in region us-east-1, skipping\n"
        "✨ Uninstall Complete ✨\n"
    )

    session = boto3.Session(region_name="us-east-1")
    create_log_ingestion_function(session, "mock-nr-license-key")
    result2 = cli_runner.invoke(
        cli,
        ["integrations", "uninstall", "--no-aws-permissions-check"],
        env={"AWS_DEFAULT_REGION": "us-east-1"},
        input="y",
    )

    assert result2.exit_code == 0
    assert result2.stdout == (
        "This will uninstall the New Relic AWS Lambda log ingestion. Are you sure you want to proceed? [y/N]: y\n"  # noqa
        "Deleting New Relic log ingestion stack 'NewRelicLogIngestion'\n"
        "Waiting for stack deletion to complete, this may take a minute... ✔️ Done\n"
        "✨ Uninstall Complete ✨\n"
    )


@mock_cloudformation
def test_integrations_uninstall_force(cli_runner):
    """
    Assert that 'newrelic-lambda integrations uninstall --force' uninstalls the log
    ingestion function/role without prompting if present
    """
    register_groups(cli)
    result = cli_runner.invoke(
        cli,
        ["integrations", "uninstall", "--no-aws-permissions-check", "--force"],
        env={"AWS_DEFAULT_REGION": "us-east-1"},
    )

    assert result.exit_code == 0
    assert result.stdout == (
        "No New Relic AWS Lambda log ingestion found in region us-east-1, skipping\n"
        "✨ Uninstall Complete ✨\n"
    )

    session = boto3.Session(region_name="us-east-1")
    create_log_ingestion_function(session, "mock-nr-license-key")
    result2 = cli_runner.invoke(
        cli,
        ["integrations", "uninstall", "--no-aws-permissions-check", "--force"],
        env={"AWS_DEFAULT_REGION": "us-east-1"},
        input="y",
    )

    assert result2.exit_code == 0
    assert result2.stdout == (
        "Deleting New Relic log ingestion stack 'NewRelicLogIngestion'\n"
        "Waiting for stack deletion to complete, this may take a minute... ✔️ Done\n"
        "✨ Uninstall Complete ✨\n"
    )
