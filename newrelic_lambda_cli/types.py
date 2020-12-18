from collections import namedtuple

INTEGRATION_INSTALL_KEYS = [
    "session",
    "verbose",
    "aws_profile",
    "aws_region",
    "aws_permissions_check",
    "aws_role_policy",
    "enable_logs",
    "memory_size",
    "linked_account_name",
    "nr_account_id",
    "nr_api_key",
    "nr_region",
    "timeout",
    "role_name",
    "enable_license_key_secret",
    "enable_cw_ingest",
    "integration_arn",
    "tags",
]

INTEGRATION_UNINSTALL_KEYS = [
    "session",
    "aws_profile",
    "aws_region",
    "aws_permissions_check",
    "nr_account_id",
    "force",
]

INTEGRATION_UPDATE_KEYS = [
    "session",
    "aws_profile",
    "aws_region",
    "aws_permissions_check",
    "enable_logs",
    "memory_size",
    "timeout",
    "role_name",
    "enable_license_key_secret",
    "tags",
]

LAYER_INSTALL_KEYS = [
    "session",
    "verbose",
    "nr_account_id",
    "nr_api_key",
    "nr_region",
    "aws_profile",
    "aws_region",
    "aws_permissions_check",
    "functions",
    "excludes",
    "layer_arn",
    "upgrade",
    "enable_extension",
    "enable_extension_function_logs",
]

LAYER_UNINSTALL_KEYS = [
    "session",
    "verbose",
    "aws_profile",
    "aws_region",
    "aws_permissions_check",
    "functions",
    "excludes",
]

SUBSCRIPTION_INSTALL_KEYS = [
    "session",
    "aws_profile",
    "aws_region",
    "aws_permissions_check",
    "functions",
    "excludes",
    "filter_pattern",
]

SUBSCRIPTION_UNINSTALL_KEYS = [
    "session",
    "aws_profile",
    "aws_region",
    "aws_permissions_check",
    "functions",
    "excludes",
]


IntegrationInstall = namedtuple("IntegrationInstall", INTEGRATION_INSTALL_KEYS)
IntegrationUninstall = namedtuple("IntegrationUninstall", INTEGRATION_UNINSTALL_KEYS)
IntegrationUpdate = namedtuple("IntegrationUpdate", INTEGRATION_UPDATE_KEYS)

LayerInstall = namedtuple("LayerInstall", LAYER_INSTALL_KEYS)
LayerUninstall = namedtuple("LayerUninstall", LAYER_UNINSTALL_KEYS)

SubscriptionInstall = namedtuple("SubscriptionInstall", SUBSCRIPTION_INSTALL_KEYS)
SubscriptionUninstall = namedtuple("SubscriptionUninstall", SUBSCRIPTION_UNINSTALL_KEYS)
