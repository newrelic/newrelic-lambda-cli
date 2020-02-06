from moto import mock_lambda

from newrelic_lambda_cli.cli import cli, register_groups


@mock_lambda
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
        ],
        env={"AWS_DEFAULT_REGION": "us-east-1"},
    )

    assert result.exit_code == 1
    assert result.stdout == ""
    assert result.stderr == (
        "✖️ Could not find function: foobar\n"
        "✖️ Install Incomplete. See messages above for details.\n"
    )

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
        ],
        env={"AWS_DEFAULT_REGION": "us-east-1"},
    )

    assert result2.exit_code == 1
    assert result2.stdout == ""
    assert result2.stderr == (
        "✖️ Could not find function: foobar\n"
        "✖️ Could not find function: barbaz\n"
        "✖️ Install Incomplete. See messages above for details.\n"
    )


@mock_lambda
def test_layers_uninstall(aws_credentials, cli_runner):
    """
    Assert that 'newrelic-lambda layers uninstall' attempts to uninstall the New Relic
    layer on a function
    """
    register_groups(cli)

    result = cli_runner.invoke(
        cli,
        ["layers", "uninstall", "--no-aws-permissions-check", "--function", "foobar"],
        env={"AWS_DEFAULT_REGION": "us-east-1"},
    )

    assert result.exit_code == 1
    assert result.stdout == ""
    assert result.stderr == (
        "✖️ Could not find function: foobar\n"
        "✖️ Uninstall Incomplete. See messages above for details.\n"
    )

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
        ],
        env={"AWS_DEFAULT_REGION": "us-east-1"},
    )

    assert result2.exit_code == 1
    assert result2.stdout == ""
    assert result2.stderr == (
        "✖️ Could not find function: foobar\n"
        "✖️ Could not find function: barbaz\n"
        "✖️ Uninstall Incomplete. See messages above for details.\n"
    )
