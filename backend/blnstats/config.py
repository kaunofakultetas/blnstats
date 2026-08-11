############################################################
#  [*] Config — env-driven settings classes (UNUSED)
#
#  Classic Flask config-class layout fed from .env via
#  python-dotenv. Dead code twice over: nothing in the
#  backend imports this module (the app configures itself
#  inline in blnstats/__init__.py), and it cannot even be
#  imported as-is — TestingConfig reads Config.DATABASE_NAME,
#  an attribute that does not exist, so the import raises
#  AttributeError.
############################################################


import os
from dotenv import load_dotenv

# the class attributes below resolve at import time — .env must load first
load_dotenv()









############################################################
# Config
############################################################
#
# The shared defaults: every value comes from the
# environment with a fallback, so a bare checkout still
# constructs. Numeric values are int()-cast at import time
# — a malformed env var crashes the import.
#
# Used by:
#   - the three subclasses below; nothing imports this
#     module at the moment
############################################################

class Config:
    # Secret key for session management
    SECRET_KEY = os.getenv('SECRET_KEY', 'your-secret-key')

    # Bitcoin RPC settings
    BITCOIN_RPC_USER = os.getenv('BITCOIN_RPC_USER', '')
    BITCOIN_RPC_PASSWORD = os.getenv('BITCOIN_RPC_PASSWORD', '')
    BITCOIN_RPC_HOST = os.getenv('BITCOIN_RPC_HOST', '')
    BITCOIN_RPC_PORT = int(os.getenv('BITCOIN_RPC_PORT', 8332))

    # Electrum server settings
    ELECTRUM_SERVER_HOST = os.getenv('ELECTRUM_SERVER_HOST', '')
    ELECTRUM_SERVER_PORT = int(os.getenv('ELECTRUM_SERVER_PORT', 50001))

    # Lightning Network research settings
    LN_RESEARCH_TIMEFRAME = os.getenv('LN_RESEARCH_TIMEFRAME', '20230924')

    # Chart generation settings
    CHART_DPI = int(os.getenv('CHART_DPI', 1000))
    CHART_DATE_CUTOFF = os.getenv('CHART_DATE_CUTOFF', '2023-09-24')

    # Logging configuration
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FILE = os.getenv('LOG_FILE', 'app.log')

    # Cache settings
    CACHE_TYPE = os.getenv('CACHE_TYPE', 'simple')
    CACHE_DEFAULT_TIMEOUT = int(os.getenv('CACHE_DEFAULT_TIMEOUT', 300))

    # Other settings
    TOP_ENTITIES_COUNT = int(os.getenv('TOP_ENTITIES_COUNT', 50))
    DAY_OF_YEAR_FOR_CHARTS = os.getenv('DAY_OF_YEAR_FOR_CHARTS', '-06-01')









############################################################
# DevelopmentConfig
############################################################
#
# Debug on, nothing else changed.
#
# Used by:
#   - the config map below; nothing calls this at the
#     moment
############################################################

class DevelopmentConfig(Config):
    DEBUG = True
    TESTING = False









############################################################
# TestingConfig
############################################################
#
# BUG: 'test_' + Config.DATABASE_NAME — Config defines no
# DATABASE_NAME attribute, so merely importing this module
# raises AttributeError (only ProductionConfig sets one).
# Unnoticed because nothing imports config.py.
#
# Used by:
#   - the config map below; nothing calls this at the
#     moment
############################################################

class TestingConfig(Config):
    DEBUG = False
    TESTING = True
    DATABASE_NAME = 'test_' + Config.DATABASE_NAME









############################################################
# ProductionConfig
############################################################
#
# SECRET_KEY is re-read without a fallback — but os.getenv
# just returns None when it is missing, so an unset env var
# passes silently instead of failing. DATABASE_NAME's
# default is an SQLite-style filename although the app runs
# MySQL.
#
# Used by:
#   - the config map below; nothing calls this at the
#     moment
############################################################

class ProductionConfig(Config):
    DEBUG = False
    TESTING = False

    # Override these settings in production
    SECRET_KEY = os.getenv('SECRET_KEY')  # Must be set in production
    DATABASE_NAME = os.getenv('DATABASE_NAME', 'production_LnStats.db')
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'ERROR')









############################################################
# config
############################################################
#
# FLASK_ENV value → config class; get_config() resolves
# through this map.
#
# Used by:
#   - get_config (below)
############################################################

config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}









############################################################
# get_config
############################################################
#
# Maps FLASK_ENV to a config class, falling back to
# development for unknown or unset values.
#
# Used by:
#   - nothing calls this at the moment — the backend never
#     imports config.py
############################################################

def get_config():
    flask_env = os.getenv('FLASK_ENV', 'default')
    return config.get(flask_env, config['default'])
