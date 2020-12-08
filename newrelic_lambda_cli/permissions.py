# -*- coding: utf-8 -*-

import click
import botocore

from newrelic_lambda_cli.types import (
    IntegrationInstall,
    IntegrationUninstall,
    LayerInstall,
    LayerUninstall,
    SubscriptionInstall,
    SubscriptionUninstall,
)


def check_permissions(session, actions, resources=None, context=None):
    """
    Checks whether an IAM user can perform specified actions. Also optionally checks
    actions against AWS resources and/or contexts.

    :param session: A boto3 session instance
    :param actions: A list of AWS actions to check
    :param resources: An optional list of AWS resources to check actions against
    :param context: Optional AWS contexts to check actions against
    :returns: A list of actions denied by AWS due to insufficient permissions
    :rtype: list
    """
    if not actions:
        return []

    actions = list(set(actions))

    if resources is None:
        resources = ["*"]

    context_entries = [{}]
    if context is not None:
        context_entries = [
            {
                "ContextKeyName": key,
                "ContextKeyValues": [str(val) for val in values],
                "ContextKeyType": "string",
            }
            for key, values in context.items()
        ]

    # See here for docs:
    # https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/iam.html
    iam = session.client("iam")
    sts = session.client("sts")

    # See here for docs:
    # https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/sts.html#STS.Client.get_caller_identity
    caller = sts.get_caller_identity()
    caller_arn = caller["Arn"]

    # See here for docs:
    # https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/iam.html#IAM.Client.simulate_principal_policy
    results = None
    try:
        results = iam.simulate_principal_policy(
            PolicySourceArn=caller_arn,
            ActionNames=actions,
            ResourceArns=resources,
            ContextEntries=context_entries,
        )["EvaluationResults"]
    except botocore.exceptions.ClientError:
        raise click.UsageError(
            "Error simulating IAM policies, try passing --no-aws-permissions-check to "
            "override."
        )
    return sorted(
        [
            result["EvalActionName"]
            for result in results
            if result["EvalDecision"] != "allowed"
        ]
    )


def ensure_integration_install_permissions(input):
    """
    Ensures that the current AWS session has the necessary permissions to install the
    New Relic AWS Lambda Integration.

    :param input: An IntegrationInstall instance
    """
    assert isinstance(input, IntegrationInstall)

    needed_permissions = check_permissions(
        input.session,
        actions=[
            "cloudformation:CreateChangeSet",
            "cloudformation:CreateStack",
            "cloudformation:DescribeStacks",
            "cloudformation:ExecuteChangeSet",
            "iam:AttachRolePolicy",
            "iam:CreateRole",
            "iam:GetRole",
            "iam:PassRole",
            "lambda:AddPermission",
            "lambda:CreateFunction",
            "lambda:GetFunction",
            "s3:GetObject",
            "serverlessrepo:CreateCloudFormationChangeSet",
        ],
    )

    if needed_permissions:
        message = [
            "The following AWS permissions are needed to install the New Relic AWS "
            "Lambda integration:\n"
        ]
        for needed_permission in needed_permissions:
            message.append(" * %s" % needed_permission)
        message.append("\nEnsure your AWS user has these permissions and try again.")
        raise click.UsageError("\n".join(message))


def ensure_integration_uninstall_permissions(input):
    """
    Ensures that the current AWS session has the necessary permissions to uninstall the
    New Relic AWS Lambda Integration.

    :param input: An IntegrationUninstall instance
    """
    assert isinstance(input, IntegrationUninstall)

    needed_permissions = check_permissions(
        input.session,
        actions=[
            "cloudformation:DeleteStack",
            "cloudformation:DescribeStacks",
            "lambda:GetFunction",
        ],
    )

    if needed_permissions:
        message = [
            "The following AWS permissions are needed to uninstall the New Relic AWS "
            "Lambda integration:\n"
        ]
        for needed_permission in needed_permissions:
            message.append(" * %s" % needed_permission)
        message.append("\nEnsure your AWS user has these permissions and try again.")
        raise click.UsageError("\n".join(message))


def ensure_layer_install_permissions(input):
    """
    Ensures that the current AWS session has the necessary permissions to install the
    New Relic AWS Lambda layer and log subscription.

    :param input: A LayerInstall instance
    """
    assert isinstance(input, LayerInstall)
    needed_permissions = check_permissions(
        input.session,
        actions=["lambda:GetFunction", "lambda:UpdateFunctionConfiguration"],
    )

    if needed_permissions:
        message = [
            "The following AWS permissions are needed to install the New Relic AWS "
            "Lambda layer:\n"
        ]

        for needed_permission in needed_permissions:
            message.append(" * %s" % needed_permission)

        message.append("\nEnsure your AWS user has these permissions and try again.")

        raise click.UsageError("\n".join(message))


def ensure_layer_uninstall_permissions(input):
    """
    Ensures that the current AWS session has the necessary permissions to uninstall the
    New Relic AWS Lambda layer and log subscription.

    :param input: A LayerUninstall instance
    """
    assert isinstance(input, LayerUninstall)
    needed_permissions = check_permissions(
        input.session,
        actions=["lambda:GetFunction", "lambda:UpdateFunctionConfiguration"],
    )

    if needed_permissions:
        message = [
            "The following AWS permissions are needed to uninstall the New Relic AWS "
            "Lambda layer:\n"
        ]
        for needed_permission in needed_permissions:
            message.append(" * %s" % needed_permission)
        message.append("\nEnsure your AWS user has these permissions and try again.")
        raise click.UsageError("\n".join(message))


def ensure_function_list_permissions(session):
    """
    Ensures that the current AWS session has the necessary permissions to list the
    functions with New Relic AWS Lambda layers.

    :param session: A boto3 session
    """
    needed_permissions = check_permissions(session, actions=["lambda:ListFunctions"])
    if needed_permissions:
        message = ["The following AWS permissions are needed to list functions:\n"]
        for needed_permission in needed_permissions:
            message.append(" * %s" % needed_permission)
        message.append("\nEnsure your AWS user has these permissions and try again.")
        raise click.UsageError("\n".join(message))


def ensure_subscription_install_permissions(input):
    """
    Ensures that the current AWS session has the necessary permissions to install the
    New Relic log subscription filter.

    :param input: A SubscriptionInstall instance
    """
    assert isinstance(input, SubscriptionInstall)
    needed_permissions = check_permissions(
        input.session,
        actions=[
            "lambda:GetFunction",
            "logs:DeleteSubscriptionFilter",
            "logs:DescribeSubscriptionFilters",
            "logs:PutSubscriptionFilter",
        ],
    )
    if needed_permissions:
        message = [
            "The following AWS permissions are needed to install the New Relic log "
            "subscription filter:\n"
        ]
        for needed_permission in needed_permissions:
            message.append(" * %s" % needed_permission)
        message.append("\nEnsure your AWS user has these permissions and try again.")
        raise click.UsageError("\n".join(message))


def ensure_subscription_uninstall_permissions(input):
    """
    Ensures that the current AWS session has the necessary permissions to uninstall the
    New Relic log subscription filter.

    :param input: A SubscriptionUninstall instance
    """
    assert isinstance(input, SubscriptionUninstall)
    needed_permissions = check_permissions(
        input.session,
        actions=["logs:DeleteSubscriptionFilter", "logs:DescribeSubscriptionFilters"],
    )
    if needed_permissions:
        message = [
            "The following AWS permissions are needed to uninstall the New Relic log "
            "subscription filter:\n"
        ]
        for needed_permission in needed_permissions:
            message.append(" * %s" % needed_permission)
        message.append("\nEnsure your AWS user has these permissions and try again.")
        raise click.UsageError("\n".join(message))
