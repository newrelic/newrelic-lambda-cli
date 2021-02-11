import pytest

from click.exceptions import Exit

from newrelic_lambda_cli.utils import error, is_valid_handler, parse_arn


def test_error():
    with pytest.raises(Exit):
        error("Foo bar")


def test_is_valid_handler():
    assert is_valid_handler("fakeruntime", "not.a.valid.handler") is False
    assert is_valid_handler("python3.8", "newrelic_lambda_wrapper.handler") is True


def test_parse_arn():
    result = parse_arn("arn:aws:iam:us-east-1:123456789:role/FooBar")

    assert result["partition"] == "aws"
    assert result["service"] == "iam"
    assert result["region"] == "us-east-1"
    assert result["account"] == "123456789"
    assert result["resourcetype"] == "role"
    assert result["resource"] == "FooBar"

    result = parse_arn("arn:aws:lambda:us-east-1:123456789:FooBar")

    assert result["resourcetype"] is None
    assert result["resource"] == "FooBar"

    result = parse_arn("arn:aws:lambda:us-east-1:123456789:Foo:Bar")

    assert result["resourcetype"] == "Foo"
    assert result["resource"] == "Bar"
