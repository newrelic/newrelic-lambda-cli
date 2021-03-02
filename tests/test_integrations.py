from __future__ import absolute_import

import boto3
import botocore
from moto import (
    mock_cloudformation,
    mock_iam,
    mock_lambda,
    mock_sts,
)
import pytest
from unittest.mock import call, patch, MagicMock, ANY

from newrelic_lambda_cli.integrations import (
    _check_for_ingest_stack,
    _create_log_ingestion_function,
    _create_role,
    _get_cf_stack_status,
    _get_role,
    _import_log_ingestion_function,
    remove_log_ingestion_function,
    install_license_key,
    remove_license_key,
    _get_license_key_policy_arn,
    get_aws_account_id,
    update_log_ingestion_function,
    remove_integration_role,
    install_log_ingestion,
    update_log_ingestion,
)

from .conftest import integration_install, integration_uninstall, integration_update


def test__check_for_ingest_stack_none_when_not_found():
    """
    Asserts that _check_for_ingestion_stack returns None if not present.
    """
    describe_stack_mock = {
        "client.return_value.describe_stacks.side_effect": botocore.exceptions.ClientError(
            {"ResponseMetadata": {"HTTPStatusCode": 404}}, "test"
        )
    }
    session = MagicMock(**describe_stack_mock)
    assert _check_for_ingest_stack(session) is None


def test__check_for_ingest_stack_status_when_found():
    """
    Asserts that _check_for_ingestion_stack returns the ingestion stack if present.
    """
    describe_stack_mock = {
        "client.return_value.describe_stacks.return_value": {
            "Stacks": [{"StackStatus": "CREATE_COMPLETE"}]
        }
    }
    session = MagicMock(**describe_stack_mock)
    assert _check_for_ingest_stack(session) == "CREATE_COMPLETE"


@patch("newrelic_lambda_cli.integrations.success")
def test__create_log_ingestion_function__defaults(success_mock):
    session = MagicMock()
    with patch.object(session, "client") as mock_client_factory:
        cf_mocks = {"create_change_set.return_value": {"Id": "arn:something"}}
        sar_client = MagicMock(name="serverlessrepo")
        cf_client = MagicMock(name="cloudformation", **cf_mocks)
        mock_client_factory.side_effect = [cf_client, sar_client]

        _create_log_ingestion_function(
            integration_install(
                session=session, enable_logs=False, memory_size=128, timeout=30
            ),
            "test_key",
        )

        cf_client.assert_has_calls(
            [
                call.create_change_set(
                    StackName="NewRelicLogIngestion",
                    TemplateURL=ANY,
                    Parameters=[
                        {"ParameterKey": "MemorySize", "ParameterValue": str(128)},
                        {"ParameterKey": "NRLicenseKey", "ParameterValue": "test_key"},
                        {"ParameterKey": "NRLoggingEnabled", "ParameterValue": "False"},
                        {"ParameterKey": "Timeout", "ParameterValue": str(30)},
                    ],
                    Capabilities=["CAPABILITY_IAM"],
                    Tags=[],
                    ChangeSetType="CREATE",
                    ChangeSetName=ANY,
                )
            ]
        )
        cf_client.assert_has_calls(
            [call.execute_change_set(ChangeSetName="arn:something")]
        )
        success_mock.assert_called_once()


@patch("newrelic_lambda_cli.integrations.success")
def test__create_log_ingestion_function__opts(success_mock):
    session = MagicMock()
    with patch.object(session, "client") as mock_client_factory:
        cf_mocks = {"create_change_set.return_value": {"Id": "arn:something"}}
        sar_client = MagicMock(name="serverlessrepo")
        cf_client = MagicMock(name="cloudformation", **cf_mocks)
        mock_client_factory.side_effect = [cf_client, sar_client]

        _create_log_ingestion_function(
            integration_install(
                session=session,
                enable_logs=True,
                memory_size=256,
                role_name="CustomExecRole",
                timeout=60,
            ),
            "test_key",
        )

        cf_client.assert_has_calls(
            [
                call.create_change_set(
                    StackName="NewRelicLogIngestion",
                    TemplateURL=ANY,
                    Parameters=[
                        {"ParameterKey": "MemorySize", "ParameterValue": str(256)},
                        {"ParameterKey": "NRLicenseKey", "ParameterValue": "test_key"},
                        {"ParameterKey": "NRLoggingEnabled", "ParameterValue": "True"},
                        {"ParameterKey": "Timeout", "ParameterValue": str(60)},
                        {
                            "ParameterKey": "FunctionRole",
                            "ParameterValue": "CustomExecRole",
                        },
                    ],
                    Capabilities=[],
                    Tags=[],
                    ChangeSetType="CREATE",
                    ChangeSetName=ANY,
                )
            ]
        )
        cf_client.assert_has_calls(
            [call.execute_change_set(ChangeSetName="arn:something")]
        )
        success_mock.assert_called_once()


@patch("newrelic_lambda_cli.integrations.success")
def test_remove_log_ingestion_function(success_mock):
    session = MagicMock()

    remove_log_ingestion_function(integration_uninstall(session=session))

    session.assert_has_calls(
        [
            call.client("cloudformation"),
            call.client().describe_stacks(StackName="NewRelicLogIngestion"),
            call.client().delete_stack(StackName="NewRelicLogIngestion"),
        ],
        any_order=True,
    )
    success_mock.assert_called_once()


@patch("newrelic_lambda_cli.integrations.success")
def test_remove_log_ingestion_function_not_present(success_mock):
    describe_stack_mock = {
        "client.return_value.describe_stacks.side_effect": botocore.exceptions.ClientError(
            {"ResponseMetadata": {"HTTPStatusCode": 404}}, "test"
        )
    }
    session = MagicMock(**describe_stack_mock)

    remove_log_ingestion_function(integration_uninstall(session=session))

    session.assert_has_calls(
        [
            call.client("cloudformation"),
            call.client().describe_stacks(StackName="NewRelicLogIngestion"),
        ],
        any_order=True,
    )
    success_mock.assert_not_called()


@mock_cloudformation
def test__get_cf_stack_status(aws_credentials):
    session = boto3.Session(region_name="us-east-1")
    assert _get_cf_stack_status(session, "foo-bar-baz") is None


@patch("newrelic_lambda_cli.integrations.success")
def test_install_license_key(success_mock):
    session = MagicMock()
    with patch.object(session, "client") as mock_client_factory:
        cf_mocks = {
            "describe_stacks.side_effect": botocore.exceptions.ClientError(
                {"ResponseMetadata": {"HTTPStatusCode": 404}}, "test"
            ),
            "create_change_set.return_value": {"Id": "arn:something"},
        }
        cf_client = MagicMock(name="cloudformation", **cf_mocks)
        mock_client_factory.side_effect = [cf_client, cf_client]

        result = install_license_key(integration_install(session=session), "1234abcd")
        assert result is True

        cf_client.assert_has_calls(
            [
                call.create_change_set(
                    StackName="NewRelicLicenseKeySecret",
                    TemplateBody=ANY,
                    Parameters=[
                        {"ParameterKey": "LicenseKey", "ParameterValue": "1234abcd"},
                    ],
                    Capabilities=["CAPABILITY_NAMED_IAM"],
                    Tags=[],
                    ChangeSetType="CREATE",
                    ChangeSetName=ANY,
                ),
                call.execute_change_set(ChangeSetName="arn:something"),
            ],
            any_order=True,
        )
        success_mock.assert_called_once()


@patch("newrelic_lambda_cli.integrations.success")
def test_install_license_key__already_installed(success_mock):
    session = MagicMock()
    with patch.object(session, "client") as mock_client_factory:
        cf_mocks = {
            "describe_stacks.return_value": {
                "Stacks": [{"StackStatus": "CREATE_COMPLETE"}]
            },
        }
        cf_client = MagicMock(name="cloudformation", **cf_mocks)
        mock_client_factory.side_effect = [cf_client, cf_client]

        result = install_license_key(integration_install(session=session), "1234abcd")
        assert result is True

        cf_client.assert_has_calls(
            [
                call.describe_stacks(StackName="NewRelicLicenseKeySecret"),
            ],
            any_order=True,
        )
        success_mock.assert_called()


@patch("newrelic_lambda_cli.integrations.success")
def test_remove_license_key(success_mock):
    session = MagicMock()
    with patch.object(session, "client") as mock_client_factory:
        cf_client = MagicMock(name="cloudformation")
        mock_client_factory.side_effect = cf_client

        remove_license_key(integration_uninstall(session=session))

        cf_client.assert_has_calls(
            [call().delete_stack(StackName="NewRelicLicenseKeySecret")],
            any_order=True,
        )
        success_mock.assert_called_once()


def test__get_license_key_policy_arn():
    session = MagicMock()
    with patch.object(session, "client") as mock_client_factory:
        cf_client = MagicMock(name="cloudformation")
        mock_client_factory.side_effect = cf_client

        _get_license_key_policy_arn(session)

        cf_client.assert_has_calls(
            [call().describe_stacks(StackName="NewRelicLicenseKeySecret")],
            any_order=True,
        )


@mock_cloudformation
def test__create_role(aws_credentials):
    session = boto3.Session(region_name="us-east-1")
    assert (
        _create_role(integration_install(session=session, nr_account_id=12345)) is None
    )


@mock_iam
def test__get_role(aws_credentials):
    session = boto3.Session(region_name="us-east-1")
    assert _get_role(session, "arn:aws:iam::1234567890:role/foobar") is None


@mock_cloudformation
def test__import_log_ingestion_function(aws_credentials):
    session = boto3.Session(region_name="us-east-1")
    # FIXME: For some reason moto raises a "NoCap" KeyError
    with pytest.raises(KeyError):
        _import_log_ingestion_function(
            integration_update(
                session=session,
                enable_logs=True,
                memory_size=1024,
                timeout=30,
                role_name="foobar",
            ),
            "foobar",
        )


@mock_sts
def test_get_aws_account_id(aws_credentials):
    session = boto3.Session(region_name="us-east-1")
    assert get_aws_account_id(session) == "123456789012"


@mock_cloudformation
@mock_lambda
@patch("newrelic_lambda_cli.integrations._get_sar_template_url", autospec=True)
@patch("newrelic_lambda_cli.integrations._create_log_ingestion_function", autospec=True)
def test_update_log_ingestion_function(
    mock_create_log_function, mock_get_sar_url, aws_credentials
):
    mock_get_sar_url.return_value = "https://amazonaws.com/blah"
    session = boto3.Session(region_name="us-east-1")

    assert update_log_ingestion_function(integration_update(session=session)) is None


def test_remove_integration_role(aws_credentials):
    mock_session = MagicMock()

    assert (
        remove_integration_role(
            integration_uninstall(nr_account_id=123456789, session=mock_session)
        )
        is None
    )

    mock_client = mock_session.client.return_value
    mock_client.describe_stacks.return_value = {"Stacks": [{"StackStatus": "peachy"}]}

    assert (
        remove_integration_role(
            integration_uninstall(nr_account_id=123456789, session=mock_session)
        )
        is None
    )

    mock_client.assert_has_calls(
        [call.describe_stacks(StackName="NewRelicLambdaIntegrationRole-123456789")]
    )
    mock_client.assert_has_calls(
        [call.delete_stack(StackName="NewRelicLambdaIntegrationRole-123456789")]
    )


def test_install_log_ingestion(aws_credentials, mock_function_config):
    mock_session = MagicMock()
    mock_client = mock_session.client.return_value
    mock_client.get_function.return_value = mock_function_config("python3.6")

    assert (
        install_log_ingestion(
            integration_install(nr_account_id=123456789, session=mock_session),
            "foobarbaz",
        )
        is True
    )

    mock_client.get_function.reset_mock(return_value=True)
    mock_client.get_function.return_value = None
    mock_client.describe_stacks.return_value = {"Stacks": [{"StackStatus": "peachy"}]}
    assert (
        install_log_ingestion(
            integration_install(nr_account_id=123456789, session=mock_session),
            "foobarbaz",
        )
        is False
    )

    mock_client.describe_stacks.reset_mock(return_value=True)
    mock_client.describe_stacks.return_value = {"Stacks": [{"StackStatus": None}]}
    assert (
        install_log_ingestion(
            integration_install(nr_account_id=123456789, session=mock_session),
            "foobarbaz",
        )
        is True
    )


def test_update_log_ingestion(aws_credentials, mock_function_config):
    mock_session = MagicMock()
    mock_client = mock_session.client.return_value
    mock_client.get_function.return_value = None

    assert (
        update_log_ingestion(
            integration_update(session=mock_session),
        )
        is False
    )

    mock_client.get_function.reset_mock(return_value=True)
    mock_client.get_function.return_value = mock_function_config("python3.6")
    mock_client.describe_stacks.return_value = {"Stacks": [{"StackStatus": None}]}

    assert (
        update_log_ingestion(
            integration_update(session=mock_session),
        )
        is False
    )

    mock_client.describe_stacks.reset_mock(return_value=True)
    mock_client.describe_stacks.return_value = {"Stacks": [{"StackStatus": "peachy"}]}

    assert (
        update_log_ingestion(
            integration_update(session=mock_session),
        )
        is True
    )
