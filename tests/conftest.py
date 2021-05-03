from click.testing import CliRunner
import os
import pytest

from newrelic_lambda_cli.types import (
    INTEGRATION_INSTALL_KEYS,
    INTEGRATION_UNINSTALL_KEYS,
    INTEGRATION_UPDATE_KEYS,
    LAYER_INSTALL_KEYS,
    LAYER_UNINSTALL_KEYS,
    SUBSCRIPTION_INSTALL_KEYS,
    SUBSCRIPTION_UNINSTALL_KEYS,
    IntegrationInstall,
    IntegrationUninstall,
    IntegrationUpdate,
    LayerInstall,
    LayerUninstall,
    SubscriptionInstall,
    SubscriptionUninstall,
)


def _mock_function_config(runtime):
    return {
        "Configuration": {
            "Layers": [{"Arn": "existing_layer_arn"}],
            "FunctionName": "aws-python3-dev-hello",
            "FunctionArn": "arn:aws:lambda:us-east-1:5558675309:function:aws-python3-dev-hello",  # noqa
            "Environment": {
                "Variables": {
                    "EXISTING_ENV_VAR": "Hello World",
                    "NEW_RELIC_ACCOUNT_ID": 123,
                }
            },
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


@pytest.fixture(scope="function")
def aws_credentials():
    """Mocked AWS Credentials for moto."""
    os.environ["AWS_ACCESS_KEY_ID"] = "testing"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
    os.environ["AWS_SECURITY_TOKEN"] = "testing"
    os.environ["AWS_SESSION_TOKEN"] = "testing"


def integration_install(**kwargs):
    assert all(key in INTEGRATION_INSTALL_KEYS for key in kwargs)
    return IntegrationInstall(
        **{key: kwargs.get(key) for key in INTEGRATION_INSTALL_KEYS}
    )


def integration_uninstall(**kwargs):
    assert all(key in INTEGRATION_UNINSTALL_KEYS for key in kwargs)
    return IntegrationUninstall(
        **{key: kwargs.get(key) for key in INTEGRATION_UNINSTALL_KEYS}
    )


def integration_update(**kwargs):
    assert all(key in INTEGRATION_UPDATE_KEYS for key in kwargs)
    return IntegrationUpdate(
        **{key: kwargs.get(key) for key in INTEGRATION_UPDATE_KEYS}
    )


def layer_install(**kwargs):
    assert all(key in LAYER_INSTALL_KEYS for key in kwargs)
    return LayerInstall(**{key: kwargs.get(key) for key in LAYER_INSTALL_KEYS})


def layer_uninstall(**kwargs):
    assert all(key in LAYER_UNINSTALL_KEYS for key in kwargs)
    return LayerUninstall(**{key: kwargs.get(key) for key in LAYER_UNINSTALL_KEYS})


def subscription_install(**kwargs):
    assert all(key in SUBSCRIPTION_INSTALL_KEYS for key in kwargs)
    return SubscriptionInstall(
        **{key: kwargs.get(key) for key in SUBSCRIPTION_INSTALL_KEYS}
    )


def subscription_uninstall(**kwargs):
    assert all(key in SUBSCRIPTION_UNINSTALL_KEYS for key in kwargs)
    return SubscriptionUninstall(
        **{key: kwargs.get(key) for key in SUBSCRIPTION_UNINSTALL_KEYS}
    )
