from newrelic_lambda_cli.layers import _add_new_relic, _remove_new_relic


def test_add_new_relic(mock_function_config):
    config = mock_function_config("python3.7")
    assert config["Configuration"]["Handler"] == "original_handler"

    update_kwargs = _add_new_relic(
        config, "us-east-1", None, "12345", None, False, True, True
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


def test_remove_new_relic(mock_function_config):
    config = mock_function_config("python3.7")
    config["Configuration"]["Handler"] = "newrelic_lambda_wrapper.handler"
    config["Configuration"]["Environment"]["Variables"][
        "NEW_RELIC_LAMBDA_HANDLER"
    ] = "original_handler"

    update_kwargs = _remove_new_relic(config, "us-east-1")
    assert update_kwargs["FunctionName"] == config["Configuration"]["FunctionArn"]
    assert update_kwargs["Handler"] == "original_handler"
    assert not any(
        [k.startswith("NEW_RELIC") for k in update_kwargs["Environment"]["Variables"]]
    )
