import boto3
from unittest import mock
from moto import mock_aws
from unittest.mock import MagicMock

from newrelic_lambda_cli.functions import get_aliased_functions, list_functions

from .conftest import layer_install


@mock_aws
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


@mock_aws
def test_list_functions(aws_credentials):
    session = boto3.Session(region_name="us-east-1")
    assert list(list_functions(session)) == []

    mock_session = MagicMock()
    mock_client = mock_session.client.return_value
    mock_pager = mock_client.get_paginator.return_value
    mock_pager.paginate.return_value = [
        {"Functions": [{"FunctionName": "foobar", "Layers": []}]}
    ]

    assert list(list_functions(mock_session)) == [
        {"FunctionName": "foobar", "Layers": [], "x-new-relic-enabled": False}
    ]
