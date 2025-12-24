#!/usr/bin/env python3

import json
import unittest


def migrate_config_v1_to_v2(config):
    """
    Migrate configuration schema from version 1 to version 2.

    Args:
        config (dict): Configuration dictionary in version 1 format.

    Returns:
        dict: Configuration dictionary in version 2 format.
    """
    # Example migration logic
    new_config = {
        "version": 2,
        "new_key": config.get("old_key", "default_value"),
        "additional_info": config.get("info", {}),
    }
    return new_config


def is_backward_compatible(old_config, new_config):
    """
    Check if the migration maintains backward compatibility.

    Args:
        old_config (dict): Original configuration dictionary in version 1 format.
        new_config (dict): Migrated configuration dictionary in version 2 format.

    Returns:
        bool: True if backward compatible, False otherwise.
    """
    # Example compatibility check
    return old_config.get("old_key") == new_config["new_key"]


class TestConfigMigration(unittest.TestCase):
    def test_migration(self):
        v1_config = {"version": 1, "old_key": "value", "info": {"details": "some details"}}
        expected_v2_config = {"version": 2, "new_key": "value", "additional_info": {"details": "some details"}}
        v2_config = migrate_config_v1_to_v2(v1_config)
        self.assertEqual(v2_config, expected_v2_config)
        self.assertTrue(is_backward_compatible(v1_config, v2_config))


if __name__ == "__main__":
    unittest.main()
