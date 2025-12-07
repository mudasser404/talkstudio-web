"""
Dynamic Database Router
This file handles runtime database switching based on DatabaseSettings
"""
import os


def get_database_config():
    """
    Get database configuration from DatabaseSettings model or environment
    Returns the DATABASES configuration dict for Django
    """
    # Default to SQLite
    default_config = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': os.path.join(os.path.dirname(os.path.dirname(__file__)), 'db.sqlite3'),
        }
    }

    # Check if we should use MySQL from environment or settings file
    db_config_file = os.path.join(os.path.dirname(__file__), 'db_config.json')

    if os.path.exists(db_config_file):
        import json
        try:
            with open(db_config_file, 'r') as f:
                config = json.load(f)

            if config.get('database_type') == 'mysql' and config.get('mysql_enabled'):
                return {
                    'default': {
                        'ENGINE': 'mysql.connector.django',
                        'NAME': config.get('mysql_database', ''),
                        'USER': config.get('mysql_user', 'root'),
                        'PASSWORD': config.get('mysql_password', ''),
                        'HOST': config.get('mysql_host', 'localhost'),
                        'PORT': config.get('mysql_port', 3306),
                        'OPTIONS': {
                            'charset': 'utf8mb4',
                            'use_unicode': True,
                        },
                    }
                }
        except Exception as e:
            print(f"Error loading database config: {e}")
            return default_config

    return default_config
