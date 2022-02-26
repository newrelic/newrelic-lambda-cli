from unittest.mock import Mock, MagicMock, patch

from newrelic_lambda_cli.api import NewRelicGQL

@patch('newrelic_lambda_cli.api.failure')
def test_link_account_with_errors(failure):
    mock_gql = NewRelicGQL("123456789", "foobar")
    mock_gql.query = Mock(
        return_value={
            "cloudLinkAccount": {
                "errors": [{ "message": "Foo Bar" }]
            }
        }
    )

    account = mock_gql.link_account("role_arn", "account_name")

    failure.assert_called_once_with("Error while linking account with New Relic:\nFoo Bar")
    assert account == None
