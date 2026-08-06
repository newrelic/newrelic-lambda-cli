from unittest.mock import patch, MagicMock, call, ANY

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
        [
            "integrations",
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

    integrations_mock.assert_has_calls(
        [
            call.update_log_ingestion(ANY),
            call.update_log_ingestion().__bool__(),
            call.install_license_key(ANY, ANY),
            call.install_license_key().__bool__(),
        ]
    )


@patch("newrelic_lambda_cli.cli.integrations.boto3")
@patch("newrelic_lambda_cli.cli.integrations.integrations")
@patch("newrelic_lambda_cli.cli.integrations.permissions")
def test_integrations_install_with_ingest_key_only(
    permissions_mock, integrations_mock, boto3_mock, cli_runner
):
    """
    Test install with only --nr-ingest-key (no API key)
    Should create AWS resources but skip cloud integration linking
    """
    register_groups(cli)
    result = cli_runner.invoke(
        cli,
        [
            "integrations",
            "install",
            "--nr-account-id",
            "12345678",
            "--nr-ingest-key",
            "test_ingest_key",
            "--linked-account-name",
            "test_linked_account",
            "--aws-permissions-check",
        ],
        env={"AWS_DEFAULT_REGION": "us-east-1"},
    )

    assert result.exit_code == 0, result.stderr
    assert "Using provided New Relic ingest key" in result.output
    assert "Skipping cloud integration account linking" in result.output

    boto3_mock.assert_has_calls(
        [call.Session(profile_name=None, region_name="us-east-1")]
    )

    permissions_mock.assert_has_calls(
        [call.ensure_integration_install_permissions(ANY)]
    )

    integrations_mock.assert_has_calls(
        [
            call.create_integration_role(ANY),
            call.install_log_ingestion(ANY, "test_ingest_key"),
        ],
        any_order=True,
    )


@patch("newrelic_lambda_cli.cli.integrations.boto3")
@patch("newrelic_lambda_cli.cli.integrations.integrations")
@patch("newrelic_lambda_cli.cli.integrations.permissions")
@patch("newrelic_lambda_cli.cli.integrations.api")
def test_integrations_install_with_both_keys(
    api_mock, permissions_mock, integrations_mock, boto3_mock, cli_runner
):
    """
    Test install with both --nr-ingest-key and --nr-api-key
    Should fail with usage error
    """
    register_groups(cli)
    result = cli_runner.invoke(
        cli,
        [
            "integrations",
            "install",
            "--nr-account-id",
            "12345678",
            "--nr-api-key",
            "test_api_key",
            "--nr-ingest-key",
            "test_ingest_key",
            "--linked-account-name",
            "test_linked_account",
        ],
        env={"AWS_DEFAULT_REGION": "us-east-1"},
    )

    assert result.exit_code != 0
    error_message = result.output + result.stderr
    assert (
        "Please provide either the --nr-api-key or the --nr-ingest-key flag, but not both"
        in error_message
    )


@patch("newrelic_lambda_cli.cli.integrations.boto3")
@patch("newrelic_lambda_cli.cli.integrations.integrations")
@patch("newrelic_lambda_cli.cli.integrations.permissions")
@patch("newrelic_lambda_cli.cli.integrations.api")
def test_integrations_install_with_no_keys(
    api_mock, permissions_mock, integrations_mock, boto3_mock, cli_runner
):
    """
    Test install with neither --nr-api-key nor --nr-ingest-key
    Should fail with usage error
    """
    register_groups(cli)
    result = cli_runner.invoke(
        cli,
        [
            "integrations",
            "install",
            "--nr-account-id",
            "12345678",
            "--linked-account-name",
            "test_linked_account",
        ],
        env={"AWS_DEFAULT_REGION": "us-east-1"},
    )

    assert result.exit_code != 0
    error_message = result.output + result.stderr
    assert "Please provide either --nr-api-key or --nr-ingest-key" in error_message


@patch("newrelic_lambda_cli.cli.integrations.boto3")
@patch("newrelic_lambda_cli.cli.integrations.integrations")
@patch("newrelic_lambda_cli.cli.integrations.permissions")
@patch("newrelic_lambda_cli.cli.integrations.api")
def test_integrations_install_ingest_key_with_api_key(
    api_mock, permissions_mock, integrations_mock, boto3_mock, cli_runner
):
    """
    Test install with --nr-ingest-key alongside --nr-api-key (both provided)
    This should fail as they are mutually exclusive
    """
    api_mock.validate_gql_credentials.return_value = MagicMock()
    api_mock.create_integration_account.return_value = {"id": "test_id"}
    integrations_mock.create_integration_role.return_value = True

    register_groups(cli)
    result = cli_runner.invoke(
        cli,
        [
            "integrations",
            "install",
            "--nr-account-id",
            "12345678",
            "--nr-api-key",
            "test_api_key",
            "--nr-ingest-key",
            "test_ingest_key",
            "--linked-account-name",
            "test_linked_account",
        ],
        env={"AWS_DEFAULT_REGION": "us-east-1"},
    )

    assert result.exit_code != 0
    error_message = result.output + result.stderr
    assert (
        "Please provide either the --nr-api-key or the --nr-ingest-key flag, but not both"
        in error_message
    )


@patch("newrelic_lambda_cli.cli.integrations.boto3")
@patch("newrelic_lambda_cli.cli.integrations.integrations")
@patch("newrelic_lambda_cli.cli.integrations.permissions")
def test_integrations_update_with_ingest_key(
    permissions_mock, integrations_mock, boto3_mock, cli_runner
):
    """
    Test update with --nr-ingest-key instead of --nr-api-key
    """
    integrations_mock.update_log_ingestion.return_value = True
    integrations_mock.install_license_key.return_value = True

    register_groups(cli)
    result = cli_runner.invoke(
        cli,
        [
            "integrations",
            "update",
            "--nr-account-id",
            "123456789",
            "--nr-ingest-key",
            "test_ingest_key",
            "--aws-permissions-check",
        ],
        env={"AWS_DEFAULT_REGION": "us-east-1"},
    )

    assert result.exit_code == 0, result.stderr
    assert "Using provided New Relic ingest key" in result.output

    boto3_mock.assert_has_calls(
        [call.Session(profile_name=None, region_name="us-east-1")]
    )
    permissions_mock.assert_has_calls(
        [call.ensure_integration_install_permissions(ANY)]
    )

    integrations_mock.assert_has_calls(
        [
            call.update_log_ingestion(ANY),
            call.install_license_key(ANY, "test_ingest_key"),
        ],
        any_order=True,
    )


@patch("newrelic_lambda_cli.cli.integrations.boto3")
@patch("newrelic_lambda_cli.cli.integrations.integrations")
@patch("newrelic_lambda_cli.cli.integrations.permissions")
@patch("newrelic_lambda_cli.cli.integrations.api")
def test_integrations_update_with_both_keys(
    api_mock, permissions_mock, integrations_mock, boto3_mock, cli_runner
):
    """
    Test update with both --nr-api-key and --nr-ingest-key
    Should fail with usage error
    """
    register_groups(cli)
    result = cli_runner.invoke(
        cli,
        [
            "integrations",
            "update",
            "--nr-account-id",
            "123456789",
            "--nr-api-key",
            "test_api_key",
            "--nr-ingest-key",
            "test_ingest_key",
        ],
        env={"AWS_DEFAULT_REGION": "us-east-1"},
    )

    assert result.exit_code != 0
    error_message = result.output + result.stderr
    assert (
        "Please provide either the --nr-api-key or the --nr-ingest-key flag, but not both"
        in error_message
    )


@patch("newrelic_lambda_cli.cli.integrations.boto3")
@patch("newrelic_lambda_cli.cli.integrations.integrations")
@patch("newrelic_lambda_cli.cli.integrations.permissions")
@patch("newrelic_lambda_cli.cli.integrations.api")
def test_integrations_update_with_no_keys(
    api_mock, permissions_mock, integrations_mock, boto3_mock, cli_runner
):
    """
    Test update with neither --nr-api-key nor --nr-ingest-key
    Should fail with usage error
    """
    register_groups(cli)
    result = cli_runner.invoke(
        cli,
        [
            "integrations",
            "update",
            "--nr-account-id",
            "123456789",
        ],
        env={"AWS_DEFAULT_REGION": "us-east-1"},
    )

    assert result.exit_code != 0
    error_message = result.output + result.stderr
    assert "Please provide either --nr-api-key or --nr-ingest-key" in error_message
