import logging
import logging.config

import click


class ClickHandler(logging.Handler):
    formats = {
        logging.DEBUG: {'fg': 'white', 'dim': True},
        logging.INFO: {'fg': 'cyan'},
        logging.WARN: {'fg': 'yellow'},
    }

    def get_log_format(self, record):
        return self.formats.get(record.levelno, {'fg': 'red'})

    def emit(self, record):
        log_entry = self.format(record)
        click.secho(log_entry, **self.get_log_format(record))


def log_config(log_level: str) -> dict:
    """
    Setup default config. for dictConfig.
    :param log_level: str name or django debugging int
    :return: dict suitable for ``logging.config.dictConfig``
    """
    assert log_level in {'DEBUG', 'INFO', 'WARNING', 'ERROR'}, f'wrong log level {log_level}'
    return {
        'version': 1,
        'disable_existing_loggers': True,
        'formatters': {'default': {'format': '%(message)s'}, 'indent': {'format': '    %(message)s'}},
        'handlers': {
            'sasstastic': {'level': log_level, 'class': 'sasstastic.logs.ClickHandler', 'formatter': 'default'},
        },
        'loggers': {
            'sasstastic': {'handlers': ['sasstastic'], 'level': log_level, 'propagate': False},
        },
    }


def setup_logging(log_level):
    config = log_config(log_level)
    logging.config.dictConfig(config)
