from unittest.mock import Mock

from newrelic_lambda_cli.api import (
    create_integration_account,
    enable_lambda_integration,
    NewRelicGQL,
)

from .conftest import integration_install


def test_create_integration_account():
    mock_gql = NewRelicGQL("123456789", "foobar")
    mock_gql.query = Mock(
        return_value={
            "actor": {
                "account": {
                    "cloud": {
                        "linkedAccounts": [
                            {
                                "authLabel": "arn:aws:iam::123456789:role/FooBar",
                                "externalId": "123456789",
                                "name": "Foo Bar",
                            }
                        ]
                    }
                }
            }
        }
    )
    input = integration_install(nr_account_id=123456789, linked_account_name="Foo Bar")
    role = {"Role": {"Arn": "arn:aws:iam::123456789:role/FooBar"}}

    assert create_integration_account(mock_gql, input, role) == {
        "authLabel": "arn:aws:iam::123456789:role/FooBar",
        "externalId": "123456789",
        "name": "Foo Bar",
    }

    mock_gql.query = Mock(
        side_effect=(
            {"actor": {"account": {"cloud": {"linkedAccounts": []}}}},
            {
                "cloudLinkAccount": {
                    "linkedAccounts": [
                        {
                            "authLabel": "arn:aws:iam::123456789:role/FooBar",
                            "externalId": "123456789",
                            "name": "Foo Bar",
                        }
                    ]
                }
            },
        )
    )

    assert create_integration_account(mock_gql, input, role) == {
        "authLabel": "arn:aws:iam::123456789:role/FooBar",
        "externalId": "123456789",
        "name": "Foo Bar",
    }


def test_enable_lambda_integration():
    mock_gql = NewRelicGQL("123456789", "foobar")
    mock_gql.query = Mock(
        return_value={"actor": {"account": {"cloud": {"linkedAccounts": []}}}},
    )
    input = integration_install(nr_account_id=123456789, linked_account_name="Foo Bar")

    lambda_enabled = enable_lambda_integration(mock_gql, input, 123456789)
    assert (
        lambda_enabled is False
    ), "Account should be linked to enable the lambda integration"
    assert mock_gql.query.call_count == 1

    mock_gql.query = Mock(
        side_effect=(
            {
                "actor": {
                    "account": {
                        "cloud": {
                            "linkedAccounts": [
                                {
                                    "authLabel": "arn:aws:iam::123456789:role/FooBar",
                                    "externalId": "123456789",
                                    "id": 123456789,
                                    "name": "Foo Bar",
                                    "metricCollectionMode": "PUSH",
                                }
                            ]
                        }
                    }
                }
            },
        )
    )

    lambda_enabled = enable_lambda_integration(mock_gql, input, 123456789)
    assert mock_gql.query.call_count == 1
    assert (
        lambda_enabled is True
    ), "Accounts in PUSH mode (using Cloudwatch Metrics stream) should already have the Lambda integration enabled"

    mock_gql.query = Mock(
        side_effect=(
            {
                "actor": {
                    "account": {
                        "cloud": {
                            "linkedAccounts": [
                                {
                                    "authLabel": "arn:aws:iam::123456789:role/FooBar",
                                    "externalId": "123456789",
                                    "id": 123456789,
                                    "name": "Foo Bar",
                                    "metricCollectionMode": "PULL",
                                }
                            ]
                        }
                    }
                }
            },
            {
                "actor": {
                    "account": {
                        "cloud": {
                            "linkedAccount": {
                                "integrations": [
                                    {"service": {"isEnabled": True, "slug": "lambda"}}
                                ]
                            }
                        }
                    },
                }
            },
        )
    )

    lambda_enabled = enable_lambda_integration(mock_gql, input, 123456789)
    assert mock_gql.query.call_count == 2
    assert (
        lambda_enabled is True
    ), "Account is linked and already has the lambda integration enabled"

    mock_gql.query = Mock(
        side_effect=(
            {
                "actor": {
                    "account": {
                        "cloud": {
                            "linkedAccounts": [
                                {
                                    "authLabel": "arn:aws:iam::123456789:role/FooBar",
                                    "externalId": "123456789",
                                    "id": 123456789,
                                    "name": "Foo Bar",
                                    "metricCollectionMode": "PULL",
                                }
                            ]
                        }
                    }
                }
            },
            {
                "actor": {
                    "account": {"cloud": {"linkedAccount": {"integrations": []}}},
                }
            },
            {
                "cloudConfigureIntegration": {
                    "integrations": [
                        {
                            "id": 123456789,
                            "name": "Foo Bar",
                            "service": {"isEnabled": True, "slug": "lambda"},
                        }
                    ]
                }
            },
        )
    )

    lambda_enabled = enable_lambda_integration(mock_gql, input, 123456789)
    assert mock_gql.query.call_count == 3
    assert (
        lambda_enabled is True
    ), "Account is linked but didn't have the lambda integration enabled, so it should be configured"
