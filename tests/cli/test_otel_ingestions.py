from unittest.mock import patch, MagicMock, call, ANY

from newrelic_lambda_cli.cli import cli, register_groups


@patch("newrelic_lambda_cli.cli.otel_ingestions.boto3")
@patch("newrelic_lambda_cli.cli.otel_ingestions.otel_ingestions")
@patch("newrelic_lambda_cli.cli.otel_ingestions.permissions")
@patch("newrelic_lambda_cli.cli.otel_ingestions.api")
def test_otel_ingestions_install(
    api_mock, permissions_mock, otel_ingestions_mock, boto3_mock, cli_runner
):
    register_groups(cli)
    result = cli_runner.invoke(
        cli,
        [
            "otel-ingestions",
            "install",
            "--nr-account-id",
            "12345678",
            "--nr-api-key",
            "test_key",
            "--aws-permissions-check",
        ],
        env={"AWS_DEFAULT_REGION": "us-east-1"},
    )

    assert result.exit_code == 0, result.stderr

    boto3_mock.assert_has_calls(
        [call.Session(profile_name=None, region_name="us-east-1")]
    )

    permissions_mock.assert_has_calls(
        [call.ensure_integration_install_permissions(ANY)]
    )

    api_mock.assert_has_calls(
        [
            call.validate_gql_credentials(ANY, otel=True),
            call.retrieve_license_key(ANY),
        ],
        any_order=True,
    )

    otel_ingestions_mock.assert_has_calls(
        [
            call.install_otel_log_ingestion(ANY, ANY),
        ],
        any_order=True,
    )


@patch("newrelic_lambda_cli.cli.otel_ingestions.boto3")
@patch("newrelic_lambda_cli.cli.otel_ingestions.otel_ingestions")
@patch("newrelic_lambda_cli.cli.otel_ingestions.permissions")
def test_otel_ingestions_uninstall(
    permissions_mock, otel_ingestions_mock, boto3_mock, cli_runner
):
    """
    Assert that 'newrelic-lambda integrations uninstall' uninstall the log ingestion
    function/role if present
    """
    register_groups(cli)
    result = cli_runner.invoke(
        cli,
        [
            "otel-ingestions",
            "uninstall",
            "--no-aws-permissions-check",
            "--nr-account-id",
            "12345678",
        ],
        env={"AWS_DEFAULT_REGION": "us-east-1"},
        input="y\ny\ny",
    )

    assert result.exit_code == 0, result.stderr

    boto3_mock.assert_has_calls(
        [call.Session(profile_name=None, region_name="us-east-1")]
    )
    permissions_mock.assert_not_called()
    otel_ingestions_mock.assert_has_calls(
        [
            call.remove_otel_log_ingestion_function(ANY),
        ]
    )


@patch("newrelic_lambda_cli.cli.otel_ingestions.boto3")
@patch("newrelic_lambda_cli.cli.otel_ingestions.otel_ingestions")
@patch("newrelic_lambda_cli.cli.otel_ingestions.permissions")
def test_otel_ingestions_uninstall_force(
    permissions_mock, otel_ingestions_mock, boto3_mock, cli_runner
):
    """
    Test that the --force option bypasses the prompts by not providing input to the CLI runner
    """
    register_groups(cli)
    result = cli_runner.invoke(
        cli,
        [
            "otel-ingestions",
            "uninstall",
            "--nr-account-id",
            "12345678",
            "--force",
            "--aws-permissions-check",
        ],
        env={"AWS_DEFAULT_REGION": "us-east-1"},
    )

    assert result.exit_code == 0, result.stderr

    boto3_mock.assert_has_calls(
        [call.Session(profile_name=None, region_name="us-east-1")]
    )

    permissions_mock.assert_has_calls(
        [call.ensure_integration_uninstall_permissions(ANY)]
    )

    otel_ingestions_mock.assert_has_calls(
        [
            call.remove_otel_log_ingestion_function(ANY),
        ]
    )


@patch("newrelic_lambda_cli.cli.otel_ingestions.boto3")
@patch("newrelic_lambda_cli.cli.otel_ingestions.otel_ingestions")
@patch("newrelic_lambda_cli.cli.otel_ingestions.permissions")
@patch("newrelic_lambda_cli.cli.otel_ingestions.api")
def test_otel_ingestions_update(
    api_mock, permissions_mock, otel_ingestions_mock, boto3_mock, cli_runner
):
    """
    Test that the --force option bypasses the prompts by not providing input to the CLI runner
    """
    register_groups(cli)
    result = cli_runner.invoke(
        cli,
        [
            "otel-ingestions",
            "update",
            "--aws-permissions-check",
            "--nr-account-id",
            "123456789",
            "--nr-api-key",
            "foobar",
        ],
        env={"AWS_DEFAULT_REGION": "us-east-1"},
    )

    assert result.exit_code == 0, result.stderr

    boto3_mock.assert_has_calls(
        [call.Session(profile_name=None, region_name="us-east-1")]
    )
    permissions_mock.assert_has_calls(
        [call.ensure_integration_install_permissions(ANY)]
    )

    otel_ingestions_mock.assert_has_calls(
        [
            call.update_otel_log_ingestion(ANY),
            call.update_otel_log_ingestion().__bool__(),
        ]
    )
