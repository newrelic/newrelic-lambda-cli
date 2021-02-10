from newrelic_lambda_cli.utils import parse_arn


def test_parse_arn():
    result = parse_arn("arn:aws:iam:us-east-1:123456789:role/FooBar")

    assert result["partition"] == "aws"
    assert result["service"] == "iam"
    assert result["region"] == "us-east-1"
    assert result["account"] == "123456789"
