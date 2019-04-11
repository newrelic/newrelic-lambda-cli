from iopipe_cli import awslambda
from iopipe_cli import utils

import jwt
import os
import pytest

TEST_TOKEN = jwt.encode({}, "its_a_secret_to_everyone")


def _mock_function_config(runtime):
    return {
        "Configuration": {
            "Layers": [{"Arn": "existing_layer_arn"}],
            "FunctionName": "aws-python3-dev-hello",
            "FunctionArn": "arn:aws:lambda:us-east-1:5558675309:function:aws-python3-dev-hello",
            "Environment": {"Variables": {"EXISTING_ENV_VAR": "Hello World"}},
            "Handler": "original_handler",
            "Runtime": runtime,
        }
    }


def test_add_iopipe_error_no_token():
    with pytest.raises(awslambda.UpdateLambdaException):
        awslambda._add_iopipe(
            _mock_function_config("nodejs8.10"),
            "us-east-1",
            "fakeArn",
            None,
            None,
            None,
            None,
        )


# Needs to test through Click where the env var is read
# def test_add_iopipe_env_token():
#    os.environ["IOPIPE_TOKEN"] = TEST_TOKEN
#    result = awslambda._add_iopipe(fake_function_config, 'us-east-1', 'fakeArn', None, None, None, None)
#    print(result)
#    del os.environ["IOPIPE_TOKEN"]
#    assert result["Environment"]["Variables"]["IOPIPE_TOKEN"] == TEST_TOKEN
# def test_add_iopipe_env_token_override():
#    os.environ["IOPIPE_TOKEN"] = "invalid_token"
#    result = awslambda._add_iopipe(fake_function_config, 'us-east-1', 'fakeArn', None, TEST_TOKEN, None, None)
#    del os.environ["IOPIPE_TOKEN"]
#    assert result["Environment"]["Variables"]["IOPIPE_TOKEN"] == TEST_TOKEN


def test_add_iopipe_updates_handler():
    fake_function_config = _mock_function_config("nodejs8.10")
    result = awslambda._add_iopipe(
        fake_function_config, "us-east-1", "fakeArn", None, TEST_TOKEN, None, None
    )
    runtime = fake_function_config["Configuration"]["Runtime"]
    assert utils.is_valid_handler(runtime, result["Handler"])


def test_remove_iopipe_removes_handler():
    fake_function_config = _mock_function_config("nodejs8.10")
    wrapped = utils.local_apply_updates(
        fake_function_config,
        awslambda._add_iopipe(
            fake_function_config, "us-east-1", "fakeArn", None, TEST_TOKEN, None, None
        ),
    )
    runtime = fake_function_config["Configuration"]["Runtime"]
    result = awslambda._remove_iopipe(wrapped, "us-east-1", "fakeArn", None)
    assert not utils.is_valid_handler(runtime, result["Handler"])


def test_add_iopipe_keeps_existing_layers():
    fake_function_config = _mock_function_config("nodejs8.10")
    result = awslambda._add_iopipe(
        fake_function_config, "us-east-1", "fakeArn", None, TEST_TOKEN, None, None
    )
    assert "existing_layer_arn" in result["Layers"]


def test_add_iopipe_upgrade_requires_flag():
    fake_function_config = _mock_function_config("nodejs8.10")
    wrapped = utils.local_apply_updates(
        fake_function_config,
        awslambda._add_iopipe(
            fake_function_config, "us-east-1", "fakeArn", None, TEST_TOKEN, None, None
        ),
    )
    with pytest.raises(awslambda.UpdateLambdaException):
        awslambda._add_iopipe(
            wrapped, "us-east-1", "fakeArn", None, TEST_TOKEN, None, None
        )


def test_add_iopipe_upgrade_success():
    fake_function_config = _mock_function_config("nodejs8.10")
    wrapped = utils.local_apply_updates(
        fake_function_config,
        awslambda._add_iopipe(
            fake_function_config, "us-east-1", "fakeArn", None, TEST_TOKEN, None, None
        ),
    )
    assert awslambda._add_iopipe(
        wrapped, "us-east-1", "fakeArn", None, TEST_TOKEN, None, True
    )


def test_add_iopipe_upgrade_success_java8():
    fake_function_config = _mock_function_config("java8")
    wrapped = utils.local_apply_updates(
        fake_function_config,
        awslambda._add_iopipe(
            fake_function_config,
            "us-east-1",
            "fakeArn",
            None,
            TEST_TOKEN,
            "request",
            None,
        ),
    )
    assert awslambda._add_iopipe(
        wrapped, "us-east-1", "fakeArn", None, TEST_TOKEN, "request", True
    )


def test_on_off_on_again_node810():
    fake_function_config = _mock_function_config("nodejs8.10")
    runtime = fake_function_config["Configuration"]["Runtime"]
    print(fake_function_config)
    wrapped = utils.local_apply_updates(
        fake_function_config,
        awslambda._add_iopipe(
            fake_function_config, "us-east-1", "fakeArn", None, TEST_TOKEN, None, None
        ),
    )
    removal_updates = awslambda._remove_iopipe(wrapped, "us-east-1", "fakeArn", None)
    assert not utils.is_valid_handler(runtime, removal_updates["Handler"])

    unwrapped = utils.local_apply_updates(wrapped, removal_updates)
    rewrapped_updates = awslambda._add_iopipe(
        unwrapped, "us-east-1", "fakeArn", None, TEST_TOKEN, None, None
    )
    assert utils.is_valid_handler(runtime, rewrapped_updates["Handler"])


def test_on_off_on_again_java_request():
    fake_function_config = _mock_function_config("java8")
    runtime = fake_function_config["Configuration"]["Runtime"]
    print(fake_function_config)
    wrapped = utils.local_apply_updates(
        fake_function_config,
        awslambda._add_iopipe(
            fake_function_config,
            "us-east-1",
            "fakeArn",
            None,
            TEST_TOKEN,
            "request",
            None,
        ),
    )
    removal_updates = awslambda._remove_iopipe(wrapped, "us-east-1", "fakeArn", None)
    assert not utils.is_valid_handler(runtime, removal_updates["Handler"])

    unwrapped = utils.local_apply_updates(wrapped, removal_updates)
    rewrapped_updates = awslambda._add_iopipe(
        unwrapped, "us-east-1", "fakeArn", None, TEST_TOKEN, "request", None
    )
    assert utils.is_valid_handler(runtime, rewrapped_updates["Handler"])


def test_on_off_on_again_java_stream():
    fake_function_config = _mock_function_config("java8")
    runtime = fake_function_config["Configuration"]["Runtime"]
    print(fake_function_config)
    wrapped = utils.local_apply_updates(
        fake_function_config,
        awslambda._add_iopipe(
            fake_function_config,
            "us-east-1",
            "fakeArn",
            None,
            TEST_TOKEN,
            "stream",
            None,
        ),
    )
    removal_updates = awslambda._remove_iopipe(wrapped, "us-east-1", "fakeArn", None)
    assert not utils.is_valid_handler(runtime, removal_updates["Handler"])

    unwrapped = utils.local_apply_updates(wrapped, removal_updates)
    rewrapped_updates = awslambda._add_iopipe(
        unwrapped, "us-east-1", "fakeArn", None, TEST_TOKEN, "stream", None
    )
    assert utils.is_valid_handler(runtime, rewrapped_updates["Handler"])


def test_on_off_on_again_python37():
    fake_function_config = _mock_function_config("python3.7")
    runtime = fake_function_config["Configuration"]["Runtime"]
    print(fake_function_config)
    wrapped = utils.local_apply_updates(
        fake_function_config,
        awslambda._add_iopipe(
            fake_function_config, "us-east-1", "fakeArn", None, TEST_TOKEN, None, None
        ),
    )
    removal_updates = awslambda._remove_iopipe(wrapped, "us-east-1", "fakeArn", None)
    assert not utils.is_valid_handler(runtime, removal_updates["Handler"])

    unwrapped = utils.local_apply_updates(wrapped, removal_updates)
    rewrapped_updates = awslambda._add_iopipe(
        unwrapped, "us-east-1", "fakeArn", None, TEST_TOKEN, None, None
    )
    assert utils.is_valid_handler(runtime, rewrapped_updates["Handler"])
