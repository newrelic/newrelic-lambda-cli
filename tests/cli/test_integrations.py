from unittest.mock import patch, call, ANY

from newrelic_lambda_cli.cli import cli, register_groups


@patch("newrelic_lambda_cli.cli.integrations.boto3")
@patch("newrelic_lambda_cli.cli.integrations.integrations")
@patch("newrelic_lambda_cli.cli.integrations.permissions")
@patch("newrelic_lambda_cli.cli.integrations.api")
def test_integrations_install(
    api_mock, permissions_mock, integrations_mock, boto3_mock, cli_runner
):
    register_groups(cli)
    result = cli_runner.invoke(
        cli,
        [
            "integrations",
            "install",
            "--nr-account-id",
            "12345678",
            "--nr-api-key",
            "test_key",
            "--linked-account-name",
            "test_linked_account",
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
            call.validate_gql_credentials(ANY),
            call.retrieve_license_key(ANY),
            call.create_integration_account(ANY, ANY, ANY),
            call.enable_lambda_integration(ANY, ANY, ANY),
        ],
        any_order=True,
    )

    integrations_mock.assert_has_calls(
        [
            call.validate_linked_account(ANY, ANY),
            call.create_integration_role(ANY),
            call.install_log_ingestion(ANY, ANY),
        ],
        any_order=True,
    )


@patch("newrelic_lambda_cli.cli.integrations.boto3")
@patch("newrelic_lambda_cli.cli.integrations.integrations")
@patch("newrelic_lambda_cli.cli.integrations.permissions")
def test_integrations_uninstall(
    permissions_mock, integrations_mock, boto3_mock, cli_runner
):
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
        input="y\ny\ny",
    )

    assert result.exit_code == 0, result.stderr

    boto3_mock.assert_has_calls(
        [call.Session(profile_name=None, region_name="us-east-1")]
    )
    permissions_mock.assert_not_called()
    integrations_mock.assert_has_calls(
        [
            call.remove_integration_role(ANY),
            call.remove_log_ingestion_function(ANY),
        ]
    )


@patch("newrelic_lambda_cli.cli.integrations.boto3")
@patch("newrelic_lambda_cli.cli.integrations.integrations")
@patch("newrelic_lambda_cli.cli.integrations.permissions")
def test_integrations_uninstall_force(
    permissions_mock, integrations_mock, boto3_mock, cli_runner
):
    """
    Test that the --force option bypasses the prompts by not providing input to the CLI runner
    """
    register_groups(cli)
    result = cli_runner.invoke(
        cli,
        [
            "integrations",
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

    integrations_mock.assert_has_calls(
        [
            call.remove_integration_role(ANY),
            call.remove_log_ingestion_function(ANY),
        ]
    )


@patch("newrelic_lambda_cli.cli.integrations.boto3")
@patch("newrelic_lambda_cli.cli.integrations.integrations")
@patch("newrelic_lambda_cli.cli.integrations.permissions")
@patch("newrelic_lambda_cli.cli.integrations.api")
def test_integrations_update(
    api_mock, permissions_mock, integrations_mock, boto3_mock, cli_runner
):
    """
    Test that the --force option bypasses the prompts by not providing input to the CLI runner
    """
    register_groups(cli)
    result = cli_runner.invoke(
        cli,
        ["integrations", "update", "--aws-permissions-check"],
        env={"AWS_DEFAULT_REGION": "us-east-1"},
    )

    assert result.exit_code == 0, result.stderr

    boto3_mock.assert_has_calls(
        [call.Session(profile_name=None, region_name="us-east-1")]
    )
    permissions_mock.assert_has_calls(
        [call.ensure_integration_install_permissions(ANY)]
    )

    integrations_mock.assert_has_calls(
        [
            call.update_log_ingestion(ANY),
            call.update_log_ingestion().__bool__(),
            call.auto_install_license_key(ANY),
            call.auto_install_license_key().__bool__(),
        ]
    )
