import os
# basedir = os.path.abspath(os.path.dirname(__file__))

class Config(object):
    DEBUG = False
    TESTING = False
    CSRF_ENABLED = True
    AUTO_RELOAD = True
    WORKERS = 1
    RESPONSE_TIMEOUT = 600
    MAX_QUEUE_SIZE = 10

    NEXT_URL = "http://localhost:3000"

    DATABASE_URL = os.environ.get("DATABASE_URL", 'postgresql://postgres:rofl-copters@localhost/hermes')
    REDIS_URL = os.environ.get("REDIS_URL", "redis://:password@localhost:6379/0")
    CLIENT_SECRETS_FILE = os.environ.get("CLIENT_SECRETS_FILE", None)
    ACCESS_TOKEN_NAME = os.environ.get("ACCESS_TOKEN_NAME", None)
    JWT_SECRET = os.environ.get("JWT_SECRET", None)


class ProductionConfig(Config):
    DEBUG = False
    WORKERS = 2
    AUTO_RELOAD = False


class StagingConfig(Config):
    DEVELOPMENT = True
    DEBUG = True
    WORKERS = 2


class DevelopmentConfig(Config):
    DEVELOPMENT = True
    DEBUG = True
    AUTO_RELOAD = True
    WORKERS = 2

# Necessary for connecting to vscode debugger
# Cant have auto-reload with sanic
class DebugConfig(Config):
    DEVELOPMENT = True
    DEBUG = True
    AUTO_RELOAD = False


class TestingConfig(Config):
    TESTING = True

def configSwitch(env: str) -> Config:
    '''
    Takes an environment string and returns an instance
    of the appropriate config object.

    Options:
    --------
        'prod': ProductionConfig Object
        'staging': StagingConfig Object
        'dev': DevelopmentConfig Object
        'test': TestingConfig Object
        'debug': DebugConfig Object

    Raises NotImplementedError if you try to get an config
    option not included in the above list.
    '''
    options = {
        'prod': ProductionConfig(),
        'staging': StagingConfig(),
        'dev': DevelopmentConfig(),
        'test': TestingConfig(),
        'debug': DebugConfig()
    }

    try:
        config = options[env]
        return config

    except Exception as e:
        raise NotImplementedError()
        print(f'Option has not been implemented: {e}')

        return
