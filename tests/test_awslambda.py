import jwt
import pytest

from iopipe_cli import awslambda, utils

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


@pytest.fixture(
    params=utils.runtime_config_iter(),
    ids=map(lambda x: x["runtime"], utils.runtime_config_iter()),
)
def runtime_config(request):
    return request.param


def test_add_iopipe_error_no_token(runtime_config):
    with pytest.raises(awslambda.UpdateLambdaException):
        awslambda._add_iopipe(
            _mock_function_config(runtime_config.get("runtime")),
            "us-east-1",
            "fakeArn",
            None,
            None,
            runtime_config.get("java_type"),
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


def test_add_iopipe_updates_handler(runtime_config):
    fake_function_config = _mock_function_config(runtime_config.get("runtime"))
    result = awslambda._add_iopipe(
        fake_function_config,
        "us-east-1",
        "fakeArn",
        None,
        TEST_TOKEN,
        runtime_config.get("java_type"),
        None,
    )
    assert utils.is_valid_handler(runtime_config.get("runtime"), result["Handler"])


def test_remove_iopipe_removes_handler(runtime_config):
    fake_function_config = _mock_function_config(runtime_config.get("runtime"))
    wrapped = utils.local_apply_updates(
        fake_function_config,
        awslambda._add_iopipe(
            fake_function_config,
            "us-east-1",
            "fakeArn",
            None,
            TEST_TOKEN,
            runtime_config.get("java_type"),
            None,
        ),
    )
    result = awslambda._remove_iopipe(wrapped, "us-east-1", "fakeArn", None)
    assert not utils.is_valid_handler(runtime_config.get("runtime"), result["Handler"])


def test_add_iopipe_keeps_existing_layers(runtime_config):
    fake_function_config = _mock_function_config(runtime_config.get("runtime"))
    result = awslambda._add_iopipe(
        fake_function_config,
        "us-east-1",
        "fakeArn",
        None,
        TEST_TOKEN,
        runtime_config.get("java_type"),
        None,
    )
    assert "existing_layer_arn" in result["Layers"]


def test_add_iopipe_upgrade_requires_flag(runtime_config):
    fake_function_config = _mock_function_config(runtime_config.get("runtime"))
    wrapped = utils.local_apply_updates(
        fake_function_config,
        awslambda._add_iopipe(
            fake_function_config,
            "us-east-1",
            "fakeArn",
            None,
            TEST_TOKEN,
            runtime_config.get("java_type"),
            None,
        ),
    )
    with pytest.raises(awslambda.UpdateLambdaException):
        awslambda._add_iopipe(
            wrapped,
            "us-east-1",
            "fakeArn",
            None,
            TEST_TOKEN,
            runtime_config.get("java_type"),
            None,
        )


def test_add_iopipe_upgrade_success(runtime_config):
    fake_function_config = _mock_function_config(runtime_config.get("runtime"))
    wrapped = utils.local_apply_updates(
        fake_function_config,
        awslambda._add_iopipe(
            fake_function_config,
            "us-east-1",
            "fakeArn",
            None,
            TEST_TOKEN,
            runtime_config.get("java_type"),
            None,
        ),
    )
    result = awslambda._add_iopipe(
        wrapped,
        "us-east-1",
        "fakeArn",
        None,
        TEST_TOKEN,
        runtime_config.get("java_type"),
        True,
    )
    assert result


def test_on_off_on_again(runtime_config):
    fake_function_config = _mock_function_config(runtime_config.get("runtime"))
    print("Mock function: %s" % (fake_function_config,))
    wrapped = utils.local_apply_updates(
        fake_function_config,
        awslambda._add_iopipe(
            fake_function_config,
            "us-east-1",
            "fakeArn",
            None,
            TEST_TOKEN,
            runtime_config.get("java_type"),
            None,
        ),
    )
    print("Wrapped: %s" % (wrapped,))
    assert utils.is_valid_handler(
        runtime_config.get("runtime"), wrapped["Configuration"]["Handler"]
    )

    removal_updates = awslambda._remove_iopipe(wrapped, "us-east-1", "fakeArn", None)
    unwrapped = utils.local_apply_updates(wrapped, removal_updates)
    print("Unwrapped: %s" % (unwrapped,))
    assert not utils.is_valid_handler(
        runtime_config.get("runtime"), unwrapped["Configuration"]["Handler"]
    )

    rewrapped_updates = awslambda._add_iopipe(
        unwrapped,
        "us-east-1",
        "fakeArn",
        None,
        TEST_TOKEN,
        runtime_config.get("java_type"),
        None,
    )
    print("Rewrapped: %s" % (rewrapped_updates,))
    assert utils.is_valid_handler(
        runtime_config.get("runtime"), rewrapped_updates["Handler"]
    )
