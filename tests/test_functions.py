import boto3
import mock
from moto import mock_lambda
from newrelic_lambda_cli.functions import get_aliased_functions


@mock_lambda
@mock.patch("newrelic_lambda_cli.functions.list_functions", autospec=True)
def test_get_aliased_functions(mock_list_functions, aws_credentials):
    """
    Asserts that get_aliased_functions adds functions matching one of the alias filters
    """
    session = boto3.Session(region_name="us-east-1")

    assert get_aliased_functions(session, [], []) == []
    assert get_aliased_functions(session, ["foo"], []) == ["foo"]
    assert get_aliased_functions(session, ["foo", "bar"], ["bar"]) == ["foo"]
    assert get_aliased_functions(session, ["foo", "bar", "baz"], ["bar"]) == [
        "foo",
        "baz",
    ]

    mock_list_functions.return_value = [{"FunctionName": "aliased-func"}]
    assert get_aliased_functions(session, ["foo", "bar", "all"], []) == [
        "foo",
        "bar",
        "aliased-func",
    ]

    mock_list_functions.return_value = [
        {"FunctionName": "aliased-func"},
        {"FunctionName": "ignored-func"},
        {"FunctionName": "newrelic-log-ingestion"},
    ]
    assert get_aliased_functions(session, ["foo", "bar", "all"], ["ignored-func"]) == [
        "foo",
        "bar",
        "aliased-func",
    ]
