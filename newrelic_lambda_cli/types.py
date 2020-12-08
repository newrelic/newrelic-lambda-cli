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

IntegrationInstall = namedtuple("IntegrationInstall", INTEGRATION_INSTALL_KEYS)
IntegrationUninstall = namedtuple("IntegrationUninstall", INTEGRATION_UNINSTALL_KEYS)
IntegrationUpdate = namedtuple("IntegrationUpdate", INTEGRATION_UPDATE_KEYS)
