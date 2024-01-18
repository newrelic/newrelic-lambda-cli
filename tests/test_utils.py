import pytest

from botocore.exceptions import BotoCoreError, NoCredentialsError, NoRegionError
from click.exceptions import BadParameter, UsageError

from newrelic_lambda_cli.utils import (
    error,
    is_valid_handler,
    parse_arn,
    validate_aws_profile,
    catch_boto_errors,
    supports_lambda_extension,
)


def test_error():
    with pytest.raises(UsageError):
        error("Foo bar")


def test_is_valid_handler():
    assert is_valid_handler("fakeruntime", "not.a.valid.handler") is False
    assert is_valid_handler("python3.9", "newrelic_lambda_wrapper.handler") is True


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


def test_validate_aws_profile(aws_credentials):
    with pytest.raises(BadParameter):
        validate_aws_profile(None, "foo", "foobarbaz")


def test_catch_boto_errors():
    @catch_boto_errors
    def _boto_core_error():
        raise BotoCoreError()

    with pytest.raises(UsageError):
        _boto_core_error()

    @catch_boto_errors
    def _no_credentials_error():
        raise NoCredentialsError()

    with pytest.raises(UsageError):
        _no_credentials_error()

    @catch_boto_errors
    def _no_region_error():
        raise NoRegionError()

    with pytest.raises(UsageError):
        _no_region_error()


def test_supports_lambda_extension():
    assert all(
        supports_lambda_extension(runtime)
        for runtime in (
            "dotnetcore3.1",
            "java17",
            "java11",
            "java8.al2",
            "nodejs12.x",
            "nodejs14.x",
            "nodejs16.x",
            "nodejs18.x",
            "nodejs20.x",
            "provided",
            "provided.al2",
            "python3.7",
            "python3.8",
            "python3.9",
            "python3.10",
            "python3.11",
        )
    )
    assert not any(
        supports_lambda_extension(runtime) for runtime in ("python2.7", "python3.6")
    )
