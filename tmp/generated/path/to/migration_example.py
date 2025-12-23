#!/usr/bin/env python3

import json
import unittest

class ConfigMigration:
    def __init__(self, old_config):
        self.old_config = old_config

    def migrate(self):
        # Example migration logic: add a new key 'new_key' with default value if not present
        new_config = self.old_config.copy()
        if 'new_key' not in new_config:
            new_config['new_key'] = 'default_value'
        return new_config

class TestConfigMigration(unittest.TestCase):
    def test_migration_with_new_key(self):
        old_config = {
            'old_key': 'old_value'
        }
        migrator = ConfigMigration(old_config)
        new_config = migrator.migrate()
        self.assertIn('new_key', new_config)
        self.assertEqual(new_config['new_key'], 'default_value')

    def test_migration_with_existing_new_key(self):
        old_config = {
            'old_key': 'old_value',
            'new_key': 'existing_value'
        }
        migrator = ConfigMigration(old_config)
        new_config = migrator.migrate()
        self.assertIn('new_key', new_config)
        self.assertEqual(new_config['new_key'], 'existing_value')

if __name__ == '__main__':
    unittest.main()
