import boto3
from moto import mock_lambda

from newrelic_lambda_cli.layers import _add_new_relic, _remove_new_relic

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
