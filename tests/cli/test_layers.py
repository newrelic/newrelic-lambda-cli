from moto import mock_aws

from newrelic_lambda_cli.cli import cli, register_groups


@mock_aws
def test_layers_install(aws_credentials, cli_runner):
    """
    Assert that 'newrelic-lambda layers install' attempts to install the New Relic
    layer on a function
    """
    register_groups(cli)

    result = cli_runner.invoke(
        cli,
        [
            "layers",
            "install",
            "--no-aws-permissions-check",
            "--function",
            "foobar",
            "--nr-account-id",
            "12345678",
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
    assert "Could not find function: foobar" in result.stderr
    assert "Install Incomplete. See messages above for details." in result.stderr

    result2 = cli_runner.invoke(
        cli,
        [
            "layers",
            "install",
            "--no-aws-permissions-check",
            "--function",
            "foobar",
            "--function",
            "barbaz",
            "--nr-account-id",
            "12345678",
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
    assert "Could not find function: foobar" in result2.stderr


@mock_aws
def test_layers_uninstall(aws_credentials, cli_runner):
    """
    Assert that 'newrelic-lambda layers uninstall' attempts to uninstall the New Relic
    layer on a function
    """
    register_groups(cli)

    result = cli_runner.invoke(
        cli,
        [
            "layers",
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
    assert "Could not find function: foobar" in result.stderr
    assert "Uninstall Incomplete. See messages above for details." in result.stderr

    result2 = cli_runner.invoke(
        cli,
        [
            "layers",
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
    assert "Could not find function: foobar" in result2.stderr
