import http
import logging
import sys
from copy import copy

from loguru import logger

from kona.config.config import settings

UVICORN_ACCESS_FMT = '%(client_addr)s - "%(request_line)s" %(status_code)s'


class BaseInterceptHandler(logging.Handler):
    def emit(self, record: logging.LogRecord):
        # Get corresponding Loguru level if it exists.
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        # Find caller from where originated the logged message.
        frame, depth = sys._getframe(6), 6
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(level, self._get_log_message(record))

    def _get_log_message(self, record: logging.LogRecord) -> str:
        return record.getMessage()


class InterceptUvicornHandler(BaseInterceptHandler):
    def _get_log_message(self, record: logging.LogRecord) -> str:
        return self.format(record)


class AccessFormatter(logging.Formatter):
    """Uvicorn Access Logging Formatter
    copy from uvicorn [logging.py](https://github.com/encode/uvicorn/blob/0.22.0/uvicorn/logging.py#L78)
    """

    def get_status_code(self, status_code: int) -> str:
        try:
            status_phrase = http.HTTPStatus(status_code).phrase
        except ValueError:
            status_phrase = ""
        status_and_phrase = "%s %s" % (status_code, status_phrase)

        return status_and_phrase

    def formatMessage(self, record: logging.LogRecord) -> str:
        recordcopy = copy(record)
        (
            client_addr,
            method,
            full_path,
            http_version,
            status_code,
        ) = recordcopy.args  # type: ignore[misc]
        status_code = self.get_status_code(int(status_code))  # type: ignore[arg-type]
        request_line = "%s %s HTTP/%s" % (method, full_path, http_version)
        recordcopy.__dict__.update(
            {
                "client_addr": client_addr,
                "request_line": request_line,
                "status_code": status_code,
            }
        )
        return super().formatMessage(recordcopy)


def initialize():
    loggers = (logging.getLogger(name) for name in logging.root.manager.loggerDict if name.startswith("uvicorn"))

    for uvicorn_logger in loggers:
        uvicorn_logger.handlers = []
        if uvicorn_logger.name.endswith("error"):
            uvicorn_logger.propagate = False

    access_formatter = AccessFormatter(UVICORN_ACCESS_FMT)

    # change handler for default uvicorn logger
    default_handler = InterceptUvicornHandler()
    access_handler = InterceptUvicornHandler()
    access_handler.setFormatter(access_formatter)

    logging.getLogger("uvicorn.access").handlers = [access_handler]

    for _log in ["uvicorn", "uvicorn.error", "fastapi"]:
        _logger = logging.getLogger(_log)
        _logger.handlers = [default_handler]

    # Intercept logger handler using by yirgachefe
    _logger = logging.getLogger("main")
    _logger.handlers = [BaseInterceptHandler()]

    logger.remove()
    logger.add(sys.stdout, level=settings.LOG_LEVEL)
    logger.add(
        settings.LOG_FILE,
        level=settings.LOG_LEVEL,
        rotation=settings.LOG_ROTATION,
        retention=settings.LOG_RETENTION,
        compression=settings.LOG_COMPRESSION,
    )
