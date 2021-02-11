from unittest.mock import patch

from newrelic_lambda_cli.subscriptions import (
    _get_log_group_name,
    create_log_subscription,
    remove_log_subscription,
)

from .conftest import subscription_install, subscription_uninstall


def test__get_log_group_name():
    assert (
        _get_log_group_name("arn:aws:lambda:us-east-1:123456789:function:FooBar")
        == "/aws/lambda/FooBar"
    )


@patch("newrelic_lambda_cli.subscriptions._create_subscription_filter", autospec=True)
@patch("newrelic_lambda_cli.subscriptions._get_subscription_filters", autospec=True)
@patch("newrelic_lambda_cli.subscriptions._remove_subscription_filter", autospec=True)
@patch("newrelic_lambda_cli.subscriptions.get_function", autospec=True)
def test_create_log_subscription(
    mock_get_function,
    mock_remove_subscription_filter,
    mock_get_subscription_filters,
    mock_create_subscription_filter,
):
    mock_get_function.side_effect = (
        None,
        {"Configuration": {"FunctionArn": "FooBarBaz"}},
        {"Configuration": {"FunctionArn": "FooBarBaz"}},
        {"Configuration": {"FunctionArn": "FooBarBaz"}},
    )
    mock_get_subscription_filters.side_effect = (
        None,
        [],
        [{"filterName": "NewRelicLogStreaming", "filterPattern": ""}],
    )
    mock_create_subscription_filter.return_value = True
    mock_remove_subscription_filter.return_value = True

    assert create_log_subscription(subscription_install(), "FooBarBaz") is False
    mock_get_function.assert_called_once_with(None, "newrelic-log-ingestion")
    mock_get_subscription_filters.assert_not_called()

    assert create_log_subscription(subscription_install(), "FooBarBaz") is False
    mock_get_subscription_filters.assert_called_once_with(None, "FooBarBaz")

    assert create_log_subscription(subscription_install(), "FooBarBaz") is True
    mock_create_subscription_filter.assert_called_once_with(
        None, "FooBarBaz", "FooBarBaz", None
    )

    assert create_log_subscription(subscription_install(), "FooBarBaz") is True
    mock_remove_subscription_filter.assert_called_once_with(
        None, "FooBarBaz", "NewRelicLogStreaming"
    )


@patch("newrelic_lambda_cli.subscriptions._get_subscription_filters", autospec=True)
@patch("newrelic_lambda_cli.subscriptions._remove_subscription_filter", autospec=True)
def test_remove_log_subscription(
    mock_remove_subscription_filter, mock_get_subscription_filters
):
    mock_get_subscription_filters.side_effect = (
        [{"filterName": "FooBar"}],
        [{"filterName": "NewRelicLogStreaming"}],
    )
    mock_remove_subscription_filter.return_value = True

    assert remove_log_subscription(subscription_uninstall(), "FooBarBaz") is True
    mock_get_subscription_filters.assert_called_once_with(None, "FooBarBaz")
    mock_remove_subscription_filter.assert_not_called()

    assert remove_log_subscription(subscription_uninstall(), "FooBarBaz") is True
    mock_remove_subscription_filter.assert_called_once_with(
        None, "FooBarBaz", "NewRelicLogStreaming"
    )
