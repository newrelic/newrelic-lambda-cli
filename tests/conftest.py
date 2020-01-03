from click.testing import CliRunner
import pytest


def _mock_function_config(runtime):
    return {
        "Configuration": {
            "Layers": [{"Arn": "existing_layer_arn"}],
            "FunctionName": "aws-python3-dev-hello",
            "FunctionArn": "arn:aws:lambda:us-east-1:5558675309:function:aws-python3-dev-hello",  # noqa
            "Environment": {"Variables": {"EXISTING_ENV_VAR": "Hello World"}},
            "Handler": "original_handler",
            "Runtime": runtime,
        }
    }


@pytest.fixture
def mock_function_config():
    return _mock_function_config


@pytest.fixture(scope="module")
def cli_runner():
    return CliRunner(mix_stderr=False)
