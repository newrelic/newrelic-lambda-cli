from moto import mock_lambda, mock_logs
import pytest

from newrelic_lambda_cli.cli import cli, register_groups


@pytest.mark.skip
@mock_lambda
@mock_logs
def test_subscriptions_install(aws_credentials, cli_runner):
    """
    Assert that 'newrelic-lambda subscriptions install' attempts to install the
    New Relic log subscription on a function.
    """
    register_groups(cli)

    result = cli_runner.invoke(
        cli,
        [
            "subscriptions",
            "install",
            "--no-aws-permissions-check",
            "--function",
            "foobar",
        ],
        env={"AWS_DEFAULT_REGION": "us-east-1"},
    )

    assert result.exit_code == 1
    assert result.stdout == ""
    assert "Install Incomplete. See messages above for details." in result.stderr

    result2 = cli_runner.invoke(
        cli,
        [
            "subscriptions",
            "install",
            "--no-aws-permissions-check",
            "--function",
            "foobar",
            "--function",
            "barbaz",
        ],
        env={"AWS_DEFAULT_REGION": "us-east-1"},
    )

    assert result2.exit_code == 1
    assert result2.stdout == ""
    assert "Install Incomplete. See messages above for details." in result2.stderr


@pytest.mark.skip
@mock_lambda
def test_subscriptions_uninstall(aws_credentials, cli_runner):
    """
    Assert that 'newrelic-lambda subscriptions uninstall' attempts to uninstall the
    New Relic log subscription on a function.
    """
    register_groups(cli)

    result = cli_runner.invoke(
        cli,
        [
            "subscriptions",
            "uninstall",
            "--no-aws-permissions-check",
            "--function",
            "foobar",
        ],
        env={"AWS_DEFAULT_REGION": "us-east-1"},
    )

    assert result.exit_code == 1
    assert result.stdout == ""
    assert "Uninstall Incomplete. See messages above for details." in result.stderr

    result2 = cli_runner.invoke(
        cli,
        [
            "subscriptions",
            "uninstall",
            "--no-aws-permissions-check",
            "--function",
            "foobar",
            "--function",
            "barbaz",
        ],
        env={"AWS_DEFAULT_REGION": "us-east-1"},
    )

    assert result2.exit_code == 1
    assert result2.stdout == ""
    assert "Uninstall Incomplete. See messages above for details." in result2.stderr
