from __future__ import absolute_import

import boto3
import botocore
from moto import mock_cloudformation
from unittest.mock import call, patch, MagicMock, ANY

from newrelic_lambda_cli.integrations import (
    check_for_ingest_stack,
    create_log_ingestion_function,
    get_cf_stack_status,
    remove_log_ingestion_function,
    install_license_key,
    update_license_key,
    remove_license_key,
    get_license_key_policy_arn,
)


def test_check_for_ingest_stack_none_when_not_found():
    """
    Asserts that check_for_ingestion_stack returns None if not present.
    """
    describe_stack_mock = {
        "client.return_value.describe_stacks.side_effect": botocore.exceptions.ClientError(
            {"ResponseMetadata": {"HTTPStatusCode": 404}}, "test"
        )
    }
    session = MagicMock(**describe_stack_mock)
    assert check_for_ingest_stack(session) is None


def test_check_for_ingest_stack_status_when_found():
    """
    Asserts that check_for_ingestion_stack returns the ingestion stack if present.
    """
    describe_stack_mock = {
        "client.return_value.describe_stacks.return_value": {
            "Stacks": [{"StackStatus": "CREATE_COMPLETE"}]
        }
    }
    session = MagicMock(**describe_stack_mock)
    assert check_for_ingest_stack(session) == "CREATE_COMPLETE"


@patch("newrelic_lambda_cli.integrations.success")
def test_create_log_ingestion_function_defaults(success_mock):
    session = MagicMock()
    with patch.object(session, "client") as mock_client_factory:
        cf_mocks = {"create_change_set.return_value": {"Id": "arn:something"}}
        sar_client = MagicMock(name="serverlessrepo")
        cf_client = MagicMock(name="cloudformation", **cf_mocks)
        mock_client_factory.side_effect = [cf_client, sar_client]

        create_log_ingestion_function(session, "test_key", False, 128, 30, None)

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
def test_create_log_ingestion_function_opts(success_mock):
    session = MagicMock()
    with patch.object(session, "client") as mock_client_factory:
        cf_mocks = {"create_change_set.return_value": {"Id": "arn:something"}}
        sar_client = MagicMock(name="serverlessrepo")
        cf_client = MagicMock(name="cloudformation", **cf_mocks)
        mock_client_factory.side_effect = [cf_client, sar_client]

        create_log_ingestion_function(
            session,
            "test_key",
            enable_logs=True,
            memory_size=256,
            timeout=60,
            role_name="CustomExecRole",
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

    remove_log_ingestion_function(session)

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

    remove_log_ingestion_function(session)

    session.assert_has_calls(
        [
            call.client("cloudformation"),
            call.client().describe_stacks(StackName="NewRelicLogIngestion"),
        ],
        any_order=True,
    )
    success_mock.assert_not_called()


@mock_cloudformation
def test_get_cf_stack_status(aws_credentials):
    session = boto3.Session(region_name="us-east-1")
    assert get_cf_stack_status(session, "foo-bar-baz") is None


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

        result = install_license_key(session, "1234abcd")
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
                    ChangeSetType="CREATE",
                    ChangeSetName=ANY,
                ),
                call.execute_change_set(ChangeSetName="arn:something"),
            ],
            any_order=True,
        )
        success_mock.assert_called_once()


@patch("newrelic_lambda_cli.integrations.success")
def test_update_license_key(success_mock):
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

        result = update_license_key(session, "1234abcd")
        assert result is True

        cf_client.assert_has_calls(
            [
                call.create_change_set(
                    StackName="NewRelicLicenseKeySecret",
                    TemplateBody=ANY,
                    Parameters=[
                        {"ParameterKey": "PolicyName", "UsePreviousValue": True},
                        {"ParameterKey": "LicenseKey", "ParameterValue": "1234abcd"},
                    ],
                    Capabilities=["CAPABILITY_NAMED_IAM"],
                    ChangeSetType="UPDATE",
                    ChangeSetName=ANY,
                ),
                call.execute_change_set(ChangeSetName="arn:something"),
            ],
            any_order=True,
        )
        success_mock.assert_called_once()


@patch("newrelic_lambda_cli.integrations.success")
def test_install_license_key_already_installed(success_mock):
    session = MagicMock()
    with patch.object(session, "client") as mock_client_factory:
        cf_mocks = {
            "describe_stacks.return_value": {
                "Stacks": [{"StackStatus": "CREATE_COMPLETE"}]
            },
        }
        cf_client = MagicMock(name="cloudformation", **cf_mocks)
        mock_client_factory.side_effect = [cf_client, cf_client]

        result = install_license_key(session, "1234abcd")
        assert result is True

        cf_client.assert_has_calls(
            [call.describe_stacks(StackName="NewRelicLicenseKeySecret"),],
            any_order=True,
        )
        success_mock.assert_not_called()


@patch("newrelic_lambda_cli.integrations.success")
def test_remove_license_key(success_mock):
    session = MagicMock()
    with patch.object(session, "client") as mock_client_factory:
        cf_client = MagicMock(name="cloudformation")
        mock_client_factory.side_effect = cf_client

        remove_license_key(session)

        cf_client.assert_has_calls(
            [call().delete_stack(StackName="NewRelicLicenseKeySecret")], any_order=True,
        )
        success_mock.assert_called_once()


def test_get_license_key_policy_arn():
    session = MagicMock()
    with patch.object(session, "client") as mock_client_factory:
        cf_client = MagicMock(name="cloudformation")
        mock_client_factory.side_effect = cf_client

        get_license_key_policy_arn(session)

        cf_client.assert_has_calls(
            [call().describe_stacks(StackName="NewRelicLicenseKeySecret")],
            any_order=True,
        )
