import logging
from logging.config import dictConfig

LOGGING_CONFIG = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '%(asctime)s %(levelname)s %(name)s %(module)s %(lineno)d - %(message)s'
        },
        'simple': {
            'format': '%(levelname)s %(message)s'
        },
    },
    'handlers': {
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose'
        },
        'file_daily': {
            'level': 'DEBUG',
            'class': 'logging.handlers.TimedRotatingFileHandler',
            'filename': './back_end.log',
            'when': 'D',  # Rotate daily
            'interval': 1,
            'backupCount': 7,  # Keep 7 backup logs
            'formatter': 'verbose'
        }
    },
    'loggers': {
        'django': {
            'handlers': ['file_daily', 'console'],
            'level': 'DEBUG',
            'propagate': True
        },
        'django.request': {
            'handlers': ['file_daily', 'console'],
            'level': 'INFO',
            'propagate': True
        },
        'back_end': {  # Example for a custom logger
            'handlers': ['file_daily', 'console'],
            'level': 'DEBUG',
            'propagate': True
        },
        '': {  # Example for a custom logger
            'handlers': ['file_daily', 'console'],
            'level': 'DEBUG',
            'propagate': True
        },
        # Add more loggers as needed
    }
}

dictConfig(LOGGING_CONFIG)