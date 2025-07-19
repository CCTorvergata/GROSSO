import logging
from config import COLORS, COLOR_RESET, LOG_FILE

class ColoredFormatter(logging.Formatter):
    def format(self, record):
        levelname = record.levelname
        color = COLORS.get(record.levelname, "")
        record.levelname = f"{color}{levelname}{COLOR_RESET}" if color else levelname
        return super().format(record)

def setup_logger():
    logger = logging.getLogger("GROSSO")
    logger.setLevel(logging.DEBUG)

    # Prevent adding multiple handlers if setup_logger is called more than once
    if not logger.handlers:
        # Console handler with color
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.DEBUG)
        console_handler.setFormatter(ColoredFormatter("%(levelname)s %(message)s"))
        logger.addHandler(console_handler)

        # File handler for errors
        file_handler = logging.FileHandler(LOG_FILE)
        file_handler.setLevel(logging.ERROR)
        file_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
        logger.addHandler(file_handler)

    logger.propagate = False
    return logger

# Initialize logger immediately when module is imported
logger = setup_logger()