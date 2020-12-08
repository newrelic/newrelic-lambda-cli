import boto3
from unittest import mock
from moto import mock_lambda
from newrelic_lambda_cli.functions import get_aliased_functions

from .conftest import layer_install


@mock_lambda
@mock.patch("newrelic_lambda_cli.functions.list_functions", autospec=True)
def test_get_aliased_functions(mock_list_functions, aws_credentials):
    """
    Asserts that get_aliased_functions adds functions matching one of the alias filters
    """
    session = boto3.Session(region_name="us-east-1")

    assert (
        get_aliased_functions(layer_install(session=session, functions=[], excludes=[]))
        == []
    )
    assert get_aliased_functions(
        layer_install(session=session, functions=["foo"], excludes=[])
    ) == ["foo"]
    assert get_aliased_functions(
        layer_install(session=session, functions=["foo", "bar"], excludes=["bar"])
    ) == ["foo"]
    assert get_aliased_functions(
        layer_install(
            session=session, functions=["foo", "bar", "baz"], excludes=["bar"]
        )
    ) == [
        "foo",
        "baz",
    ]

    mock_list_functions.return_value = [{"FunctionName": "aliased-func"}]
    assert get_aliased_functions(
        layer_install(session=session, functions=["foo", "bar", "all"], excludes=[])
    ) == [
        "foo",
        "bar",
        "aliased-func",
    ]

    mock_list_functions.return_value = [
        {"FunctionName": "aliased-func"},
        {"FunctionName": "ignored-func"},
        {"FunctionName": "newrelic-log-ingestion"},
    ]
    assert get_aliased_functions(
        layer_install(
            session=session, functions=["foo", "bar", "all"], excludes=["ignored-func"]
        )
    ) == [
        "foo",
        "bar",
        "aliased-func",
    ]
