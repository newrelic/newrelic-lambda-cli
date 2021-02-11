import boto3
from moto import mock_lambda
from unittest.mock import MagicMock

from newrelic_lambda_cli.layers import (
    _attach_license_key_policy,
    _detach_license_key_policy,
    _add_new_relic,
    _remove_new_relic,
)

from .conftest import integration_install, layer_install, layer_uninstall


@mock_lambda
def test_add_new_relic(aws_credentials, mock_function_config):
    session = boto3.Session(region_name="us-east-1")

    config = mock_function_config("python3.7")

    assert config["Configuration"]["Handler"] == "original_handler"

    update_kwargs = _add_new_relic(
        layer_install(
            session=session,
            aws_region="us-east-1",
            nr_account_id=12345,
            enable_extension=True,
            enable_extension_function_logs=True,
        ),
        config,
        nr_license_key=None,
    )

    assert update_kwargs["FunctionName"] == config["Configuration"]["FunctionArn"]
    assert update_kwargs["Handler"] == "newrelic_lambda_wrapper.handler"
    assert update_kwargs["Environment"]["Variables"]["NEW_RELIC_ACCOUNT_ID"] == "12345"
    assert (
        update_kwargs["Environment"]["Variables"]["NEW_RELIC_LAMBDA_HANDLER"]
        == config["Configuration"]["Handler"]
    )
    assert (
        update_kwargs["Environment"]["Variables"]["NEW_RELIC_LAMBDA_EXTENSION_ENABLED"]
        == "true"
    )
    assert (
        update_kwargs["Environment"]["Variables"][
            "NEW_RELIC_EXTENSION_SEND_FUNCTION_LOGS"
        ]
        == "true"
    )


@mock_lambda
def test_remove_new_relic(aws_credentials, mock_function_config):
    session = boto3.Session(region_name="us-east-1")

    config = mock_function_config("python3.7")
    config["Configuration"]["Handler"] = "newrelic_lambda_wrapper.handler"
    config["Configuration"]["Environment"]["Variables"][
        "NEW_RELIC_LAMBDA_HANDLER"
    ] = "original_handler"

    update_kwargs = _remove_new_relic(
        layer_uninstall(session=session, aws_region="us-east-1"), config
    )

    assert update_kwargs["FunctionName"] == config["Configuration"]["FunctionArn"]
    assert update_kwargs["Handler"] == "original_handler"
    assert not any(
        [k.startswith("NEW_RELIC") for k in update_kwargs["Environment"]["Variables"]]
    )


def test__attach_license_key_policy():
    mock_session = MagicMock()
    mock_client = mock_session.client.return_value

    assert (
        _attach_license_key_policy(
            mock_session,
            "arn:aws:iam::123456789:role/FooBar",
            "arn:aws:iam::123456789:policy/BarBaz",
        )
        is True
    )
    mock_client.attach_role_policy.assert_called_once_with(
        RoleName="FooBar", PolicyArn="arn:aws:iam::123456789:policy/BarBaz"
    )


def test__detach_license_key_policy():
    mock_session = MagicMock()
    mock_client = mock_session.client.return_value

    assert (
        _detach_license_key_policy(
            mock_session,
            "arn:aws:iam::123456789:role/FooBar",
            "arn:aws:iam::123456789:policy/BarBaz",
        )
        is True
    )
    mock_client.detach_role_policy.assert_called_once_with(
        RoleName="FooBar", PolicyArn="arn:aws:iam::123456789:policy/BarBaz"
    )
