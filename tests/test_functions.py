import boto3
from unittest import mock
from moto import mock_lambda
from unittest.mock import MagicMock
from click import UsageError

from newrelic_lambda_cli.functions import (
    get_aliased_functions,
    get_function,
    list_functions,
)

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


@mock_lambda
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


@mock_lambda
def test_get_function(aws_credentials):
    session = boto3.Session(region_name="us-east-1")
    string_too_big = "gexiwyttrlcyzjggibmfmbapercbmxdcgnkgfeqsdsxobmmyeheiryfxatutvljoxlglhfwctgrqloquyhffpaqdugyeiolixxrwxbrkupiugndognrrtfuzkqbaipfjwvggthgvtoziqlfugybrjikgoxzjszasahemcntjeqnmac"
    string_too_small = ""
    err_too_big = None
    try:
        get_function(session, string_too_big)
    except UsageError as ex:
        err_too_big = ex
    assert type(err_too_big) == UsageError
    err_too_small = None
    try:
        get_function(session, string_too_small)
    except UsageError as ex:
        err_too_small = ex
    assert type(err_too_small) == UsageError
    # session = boto3.Session(region_name="us-east-1")
    # assert get_function(session, 'foobar') == None
    # mock_session = MagicMock()
    # mock_client = mock_session.return_value
    # mock_get_function = mock_client.get_function.return_value
    # mock_get_function.return_value = {"Configuration": { "FunctionName": "foobar"}, "Code": {}, "Tags": {}, "Concurrency": {}}
    # mock_result = get_function(mock_session, 'foobar')
    # assert mock_result.return_value == 'foobar'
