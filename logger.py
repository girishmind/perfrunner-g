import logging.config
import sys
import types

LOGGING_CONFIG = {
    'disable_existing_loggers': False,
    'formatters': {
        'standard': {
            'format': '%(asctime)s [%(levelname)s] %(message)s',
            'datefmt': '%Y-%m-%dT%H:%M:%S',
        },
    },
    'handlers': {
        'file': {
            'class': 'logging.FileHandler',
            'filename': 'perfrunner.log',
            'formatter': 'standard',
            'mode': 'w',
        },
        'stream': {
            'class': 'logging.StreamHandler',
            'formatter': 'standard',
        },
    },
    'loggers': {
        '': {
            'handlers': ['stream', 'file'],
            'level': logging.INFO,
            'propagate': True,
        },
        'boto3': {
            'level': logging.WARNING,
        },
        'botocore': {
            'level': logging.WARNING,
        },
        'paramiko': {
            'level': logging.WARNING,
        },
        'requests': {
            'level': logging.ERROR,
        },
    },
    'version': 1,
}


def error(self, msg, *args, **kwargs):
    self.error(msg, *args, **kwargs)
    sys.exit(1)


logging.config.dictConfig(LOGGING_CONFIG)

logger = logging.getLogger()

logger.interrupt = types.MethodType(error, logger)
