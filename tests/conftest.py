import logging
from logging.handlers import RotatingFileHandler

import livevoice.core.logger  # noqa: F401  (configura el log; aquí le quitamos el archivo)


# Las pruebas simulan fallos ("sin internet", "403"); no deben ensuciar logs/livevoice.log real.
for handler in list(logging.getLogger().handlers):
    if isinstance(handler, RotatingFileHandler):
        logging.getLogger().removeHandler(handler)
        handler.close()
