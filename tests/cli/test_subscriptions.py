from moto import mock_aws

from newrelic_lambda_cli.cli import cli, register_groups


@mock_aws
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
            "--aws-region",
            "us-east-1",
        ],
        env={
            "AWS_ACCESS_KEY_ID": "testing",
            "AWS_SECRET_ACCESS_KEY": "testing",
            "AWS_SECURITY_TOKEN": "testing",
            "AWS_SESSION_TOKEN": "testing",
        },
    )
    assert result.exit_code == 1
    assert result.stdout == ""
    assert (
        "Could not find newrelic-log-ingestion function in stack: NewRelicLogIngestion. "
        "Is the New Relic AWS integration installed?"
    ) in result.stderr

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
            "--aws-region",
            "us-east-1",
        ],
        env={
            "AWS_ACCESS_KEY_ID": "testing",
            "AWS_SECRET_ACCESS_KEY": "testing",
            "AWS_SECURITY_TOKEN": "testing",
            "AWS_SESSION_TOKEN": "testing",
        },
    )

    assert result2.exit_code == 1
    assert result2.stdout == ""
    assert (
        "Could not find newrelic-log-ingestion function in stack: NewRelicLogIngestion. "
        "Is the New Relic AWS integration installed?"
    ) in result2.stderr

    result3 = cli_runner.invoke(
        cli,
        [
            "subscriptions",
            "install",
            "--no-aws-permissions-check",
            "--function",
            "foobar",
            "--function",
            "barbaz",
            "--aws-region",
            "us-east-1",
            "--stackname",
            "MyCustomStackName",
        ],
        env={
            "AWS_ACCESS_KEY_ID": "testing",
            "AWS_SECRET_ACCESS_KEY": "testing",
            "AWS_SECURITY_TOKEN": "testing",
            "AWS_SESSION_TOKEN": "testing",
        },
    )

    assert result3.exit_code == 1
    assert result3.stdout == ""
    assert (
        "Could not find newrelic-log-ingestion function in stack: MyCustomStackName. "
        "Is the New Relic AWS integration installed?"
    ) in result3.stderr


@mock_aws
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
            "--aws-region",
            "us-east-1",
        ],
        env={
            "AWS_ACCESS_KEY_ID": "testing",
            "AWS_SECRET_ACCESS_KEY": "testing",
            "AWS_SECURITY_TOKEN": "testing",
            "AWS_SESSION_TOKEN": "testing",
        },
    )

    assert result.exit_code == 1
    assert result.stdout == ""

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
            "--aws-region",
            "us-east-1",
        ],
        env={
            "AWS_ACCESS_KEY_ID": "testing",
            "AWS_SECRET_ACCESS_KEY": "testing",
            "AWS_SECURITY_TOKEN": "testing",
            "AWS_SESSION_TOKEN": "testing",
        },
    )

    assert result2.exit_code == 1
    assert result2.stdout == ""
