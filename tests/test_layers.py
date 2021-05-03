import boto3
from click import UsageError
from moto import mock_lambda
import pytest
from unittest.mock import ANY, call, MagicMock, patch

from newrelic_lambda_cli.layers import (
    _attach_license_key_policy,
    _detach_license_key_policy,
    _add_new_relic,
    _remove_new_relic,
    install,
    uninstall,
    layer_selection,
)
from newrelic_lambda_cli.utils import get_arn_prefix

from .conftest import layer_install, layer_uninstall


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

    config = mock_function_config("not.a.runtime")
    assert (
        _add_new_relic(
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
        is True
    )

    config = mock_function_config("python3.7")
    config["Configuration"]["Layers"] = [{"Arn": get_arn_prefix("us-east-1")}]
    assert (
        _add_new_relic(
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
        is True
    )

    with patch("newrelic_lambda_cli.layers.index") as mock_index:
        mock_index.return_value = []
        config = mock_function_config("python3.7")
        assert (
            _add_new_relic(
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
            is False
        )

    with patch("newrelic_lambda_cli.layers.index") as mock_index:
        with patch(
            "newrelic_lambda_cli.layers.layer_selection"
        ) as layer_selection_mock:
            mock_index.return_value = [
                {
                    "LatestMatchingVersion": {
                        "LayerVersionArn": "arn:aws:lambda:us-east-1:123456789:layer/javajava"
                    }
                },
                {
                    "LatestMatchingVersion": {
                        "LayerVersionArn": "arn:aws:lambda:us-east-1:123456789:layer/NewRelicLambdaExtension"
                    }
                },
            ]
            layer_selection_mock.return_value = [
                "arn:aws:lambda:us-east-1:123456789:layer/NewRelicLambdaExtension"
            ]

            config = mock_function_config("java11")
            _add_new_relic(
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

            layer_selection_mock.assert_called_with(mock_index.return_value, "java11")
            assert "original_handler" in config["Configuration"]["Handler"]

            # Java handler testing
            layer_selection_mock.return_value = [
                "arn:aws:lambda:us-east-1:123456789:layer/javajava"
            ]

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
            assert (
                "com.newrelic.java.HandlerWrapper::handleRequest"
                in update_kwargs["Handler"]
            )
            assert (
                "original_handler"
                in update_kwargs["Environment"]["Variables"]["NEW_RELIC_LAMBDA_HANDLER"]
            )

    with patch("newrelic_lambda_cli.layers.enquiries.choose") as mock_enquiries:
        mock_layers = [
            {
                "LatestMatchingVersion": {
                    "LayerVersionArn": "arn:aws:lambda:us-east-1:123456789:layer/javajava"
                }
            },
            {
                "LatestMatchingVersion": {
                    "LayerVersionArn": "arn:aws:lambda:us-east-1:123456789:layer/NewRelicLambdaExtension"
                }
            },
        ]
        mock_enquiries.return_value = (
            "arn:aws:lambda:us-east-1:123456789:layer/javajava"
        )

        result = layer_selection(mock_layers, "python3.7")
        assert result == [mock_enquiries.return_value]

    config = mock_function_config("python3.7")
    _add_new_relic(
        layer_install(
            session=session,
            aws_region="us-east-1",
            nr_account_id=12345,
            nr_region="staging",
            enable_extension=True,
            enable_extension_function_logs=True,
        ),
        config,
        "foobarbaz",
    )
    assert (
        "NEW_RELIC_TELEMETRY_ENDPOINT"
        in config["Configuration"]["Environment"]["Variables"]
    )

    config = mock_function_config("python3.7")
    config["Configuration"]["Environment"]["Variables"]["NEW_RELIC_FOO"] = "bar"
    config["Configuration"]["Layers"] = [{"Arn": get_arn_prefix("us-east-1")}]
    update_kwargs = _add_new_relic(
        layer_install(
            session=session,
            aws_region="us-east-1",
            nr_account_id=12345,
            enable_extension=True,
            enable_extension_function_logs=True,
            upgrade=True,
        ),
        config,
        "foobarbaz",
    )
    assert "NEW_RELIC_FOO" in update_kwargs["Environment"]["Variables"]
    assert update_kwargs["Layers"][0] != get_arn_prefix("us-east-1")

    config = mock_function_config("python3.6")
    update_kwargs = _add_new_relic(
        layer_install(
            session=session,
            aws_region="us-east-1",
            nr_account_id=12345,
            enable_extension=True,
            enable_extension_function_logs=True,
            upgrade=True,
        ),
        config,
        "foobarbaz",
    )
    assert (
        update_kwargs["Environment"]["Variables"]["NEW_RELIC_LAMBDA_EXTENSION_ENABLED"]
        == "false"
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

    config = mock_function_config("not.a.runtime")
    assert (
        _remove_new_relic(
            layer_uninstall(session=session, aws_region="us-east-1"), config
        )
        is True
    )

    config = mock_function_config("python3.7")
    config["Configuration"]["Handler"] = "what is this?"
    assert (
        _remove_new_relic(
            layer_uninstall(session=session, aws_region="us-east-1"), config
        )
        is False
    )

    config = mock_function_config("java11")
    config["Configuration"][
        "Handler"
    ] = "com.newrelic.java.HandlerWrapper::handleStreamsRequest"
    config["Configuration"]["Environment"]["Variables"][
        "NEW_RELIC_LAMBDA_HANDLER"
    ] = "original_handler"

    config["Configuration"]["Environment"]["Variables"]["NEW_RELIC_ACCOUNT_ID"] = 123

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


def test_install(aws_credentials, mock_function_config):
    mock_session = MagicMock()
    mock_session.region_name = "us-east-1"
    mock_client = mock_session.client.return_value
    mock_client.get_function.return_value = None
    assert install(layer_install(session=mock_session), "foobarbaz") is False

    mock_client.get_function.reset_mock(return_value=True)
    config = mock_function_config("not.a.runtime")
    mock_client.get_function.return_value = config
    assert install(layer_install(session=mock_session), "foobarbaz") is True

    mock_client.get_function.reset_mock(return_value=True)
    config = mock_function_config("python3.7")
    mock_client.get_function.return_value = config
    assert (
        install(
            layer_install(nr_account_id=123456789, session=mock_session), "foobarbaz"
        )
        is True
    )

    mock_client.assert_has_calls([call.get_function(FunctionName="foobarbaz")])
    mock_client.assert_has_calls(
        [
            call.update_function_configuration(
                FunctionName="arn:aws:lambda:us-east-1:5558675309:function:aws-python3-dev-hello",  # noqa
                Environment={
                    "Variables": {
                        "EXISTING_ENV_VAR": "Hello World",
                        "NEW_RELIC_ACCOUNT_ID": "123456789",
                        "NEW_RELIC_LAMBDA_HANDLER": "original_handler",
                        "NEW_RELIC_LAMBDA_EXTENSION_ENABLED": "false",
                    }
                },
                Layers=ANY,
                Handler="newrelic_lambda_wrapper.handler",
            )
        ]
    )


def test_uninstall(aws_credentials, mock_function_config):
    mock_session = MagicMock()
    mock_session.region_name = "us-east-1"
    mock_client = mock_session.client.return_value
    mock_client.get_function.return_value = None
    assert uninstall(layer_uninstall(session=mock_session), "foobarbaz") is False

    mock_client.get_function.reset_mock(return_value=True)
    config = mock_function_config("not.a.runtime")
    mock_client.get_function.return_value = config
    assert uninstall(layer_uninstall(session=mock_session), "foobarbaz") is True

    mock_client.get_function.reset_mock(return_value=True)
    config = mock_function_config("python3.7")
    mock_client.get_function.return_value = config
    assert uninstall(layer_uninstall(session=mock_session), "foobarbaz") is False

    config["Configuration"]["Handler"] = "newrelic_lambda_wrapper.handler"
    config["Configuration"]["Environment"]["Variables"][
        "NEW_RELIC_LAMBDA_HANDLER"
    ] = "foobar.handler"
    config["Configuration"]["Environment"]["Variables"]["NEW_RELIC_ACCOUNT_ID"] = 123
    config["Configuration"]["Layers"] = [{"Arn": get_arn_prefix("us-east-1")}]
    assert uninstall(layer_uninstall(session=mock_session), "foobarbaz") is True

    mock_client.assert_has_calls([call.get_function(FunctionName="foobarbaz")])
    mock_client.assert_has_calls(
        [
            call.update_function_configuration(
                FunctionName="arn:aws:lambda:us-east-1:5558675309:function:aws-python3-dev-hello",  # noqa
                Handler="foobar.handler",
                Environment={"Variables": {"EXISTING_ENV_VAR": "Hello World"}},
                Layers=[],
            )
        ]
    )
