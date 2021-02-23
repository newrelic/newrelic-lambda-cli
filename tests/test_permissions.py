from click import UsageError
from pytest import raises
from unittest.mock import ANY, call, MagicMock

from newrelic_lambda_cli.permissions import (
    check_permissions,
    ensure_integration_install_permissions,
    ensure_integration_uninstall_permissions,
    ensure_layer_install_permissions,
    ensure_layer_uninstall_permissions,
    ensure_function_list_permissions,
    ensure_subscription_install_permissions,
    ensure_subscription_uninstall_permissions,
)

from .conftest import (
    integration_install,
    integration_uninstall,
    layer_install,
    layer_uninstall,
    subscription_install,
    subscription_uninstall,
)


def test_check_permissions():
    mock_session = MagicMock()

    assert check_permissions(mock_session, []) == []

    mock_iam = MagicMock()
    mock_sts = MagicMock()
    mock_session.client.side_effect = (mock_iam, mock_sts)

    mock_sts.get_caller_identity.return_value = {"Arn": "arn:aws:iam::123456789:foobar"}
    mock_iam.simulate_principal_policy.return_value = {
        "EvaluationResults": [
            {"EvalActionName": "foo:bar", "EvalDecision": "allowed"},
            {"EvalActionName": "bar:baz", "EvalDecision": "denied"},
        ]
    }

    assert check_permissions(
        mock_session, ["foo:bar", "bar:baz"], context={"foobar": ["barbaz"]}
    ) == ["bar:baz"]


def test_ensure_integration_install_permissions():
    mock_session = MagicMock()
    mock_session.client.return_value.simulate_principal_policy.return_value = {
        "EvaluationResults": [
            {"EvalActionName": "foo:bar", "EvalDecision": "allowed"},
            {"EvalActionName": "bar:baz", "EvalDecision": "denied"},
        ]
    }

    with raises(UsageError):
        ensure_integration_install_permissions(
            integration_install(session=mock_session)
        )

    mock_session.assert_has_calls([call.client("iam"), call.client("sts")])
    mock_session.assert_has_calls(
        [
            call.client().simulate_principal_policy(
                PolicySourceArn=ANY,
                ActionNames=ANY,
                ResourceArns=["*"],
                ContextEntries=[{}],
            ),
        ],
    )


def test_ensure_integration_uninstall_permissions():
    mock_session = MagicMock()
    mock_session.client.return_value.simulate_principal_policy.return_value = {
        "EvaluationResults": [
            {"EvalActionName": "foo:bar", "EvalDecision": "allowed"},
            {"EvalActionName": "bar:baz", "EvalDecision": "denied"},
        ]
    }

    with raises(UsageError):
        ensure_integration_uninstall_permissions(
            integration_uninstall(session=mock_session)
        )

    mock_session.assert_has_calls([call.client("iam"), call.client("sts")])
    mock_session.assert_has_calls(
        [
            call.client().simulate_principal_policy(
                PolicySourceArn=ANY,
                ActionNames=ANY,
                ResourceArns=["*"],
                ContextEntries=[{}],
            ),
        ],
    )


def test_ensure_layer_install_permissions():
    mock_session = MagicMock()
    mock_session.client.return_value.simulate_principal_policy.return_value = {
        "EvaluationResults": [
            {"EvalActionName": "foo:bar", "EvalDecision": "allowed"},
            {"EvalActionName": "bar:baz", "EvalDecision": "denied"},
        ]
    }

    with raises(UsageError):
        ensure_layer_install_permissions(layer_install(session=mock_session))

    mock_session.assert_has_calls([call.client("iam"), call.client("sts")])
    mock_session.assert_has_calls(
        [
            call.client().simulate_principal_policy(
                PolicySourceArn=ANY,
                ActionNames=ANY,
                ResourceArns=["*"],
                ContextEntries=[{}],
            ),
        ],
    )


def test_ensure_layer_uninstall_permissions():
    mock_session = MagicMock()
    mock_session.client.return_value.simulate_principal_policy.return_value = {
        "EvaluationResults": [
            {"EvalActionName": "foo:bar", "EvalDecision": "allowed"},
            {"EvalActionName": "bar:baz", "EvalDecision": "denied"},
        ]
    }

    with raises(UsageError):
        ensure_layer_uninstall_permissions(layer_uninstall(session=mock_session))

    mock_session.assert_has_calls([call.client("iam"), call.client("sts")])
    mock_session.assert_has_calls(
        [
            call.client().simulate_principal_policy(
                PolicySourceArn=ANY,
                ActionNames=ANY,
                ResourceArns=["*"],
                ContextEntries=[{}],
            ),
        ],
    )


def test_ensure_function_list_permissions():
    mock_session = MagicMock()
    mock_session.client.return_value.simulate_principal_policy.return_value = {
        "EvaluationResults": [
            {"EvalActionName": "foo:bar", "EvalDecision": "allowed"},
            {"EvalActionName": "bar:baz", "EvalDecision": "denied"},
        ]
    }

    with raises(UsageError):
        ensure_function_list_permissions(mock_session)

    mock_session.assert_has_calls([call.client("iam"), call.client("sts")])
    mock_session.assert_has_calls(
        [
            call.client().simulate_principal_policy(
                PolicySourceArn=ANY,
                ActionNames=ANY,
                ResourceArns=["*"],
                ContextEntries=[{}],
            ),
        ],
    )


def test_ensure_subscription_install_permissions():
    mock_session = MagicMock()
    mock_session.client.return_value.simulate_principal_policy.return_value = {
        "EvaluationResults": [
            {"EvalActionName": "foo:bar", "EvalDecision": "allowed"},
            {"EvalActionName": "bar:baz", "EvalDecision": "denied"},
        ]
    }

    with raises(UsageError):
        ensure_subscription_install_permissions(
            subscription_install(session=mock_session)
        )

    mock_session.assert_has_calls([call.client("iam"), call.client("sts")])
    mock_session.assert_has_calls(
        [
            call.client().simulate_principal_policy(
                PolicySourceArn=ANY,
                ActionNames=ANY,
                ResourceArns=["*"],
                ContextEntries=[{}],
            ),
        ],
    )


def test_ensure_subscription_uninstall_permissions():
    mock_session = MagicMock()
    mock_session.client.return_value.simulate_principal_policy.return_value = {
        "EvaluationResults": [
            {"EvalActionName": "foo:bar", "EvalDecision": "allowed"},
            {"EvalActionName": "bar:baz", "EvalDecision": "denied"},
        ]
    }

    with raises(UsageError):
        ensure_subscription_uninstall_permissions(
            subscription_uninstall(session=mock_session)
        )

    mock_session.assert_has_calls([call.client("iam"), call.client("sts")])
    mock_session.assert_has_calls(
        [
            call.client().simulate_principal_policy(
                PolicySourceArn=ANY,
                ActionNames=ANY,
                ResourceArns=["*"],
                ContextEntries=[{}],
            ),
        ],
    )
