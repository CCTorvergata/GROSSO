import os
import subprocess
from log_config.logger_config import logger

class File:
    def __init__(self, path, root_dir):
        self.path = path
        self.name = os.path.relpath(path, root_dir)
        self.size = os.path.getsize(path)
        self.type = self._get_mime_type()
        self.kind = self._get_file_kind()

    def _get_mime_type(self):
        try:
            output = subprocess.check_output(
                ['file', '--mime-type', '-b', self.path],
                stderr=subprocess.DEVNULL,
                text=True,
                timeout=1
            )
            return output.strip()
        except subprocess.TimeoutExpired:
            logger.warning(f"Timeout checking MIME type for {self.path}")
            return 'unknown'
        except Exception as e:
            logger.error(f"Error getting MIME type for {self.path}: {e}")
            return 'unknown'

    def _get_file_kind(self):
        try:
            desc = subprocess.check_output(
                ['file', '-b', self.path],
                stderr=subprocess.DEVNULL,
                text=True,
                timeout=1
            ).lower()
            kinds = {
                'directory': 'directory',
                'text': 'text',
                'executable': 'executable',
                'image': 'image',
                'archive': 'archive'
            }
            return next((k for k in kinds if k in desc), 'binary')
        except subprocess.TimeoutExpired:
            logger.warning(f"Timeout checking file kind for {self.path}")
            return 'unknown'
        except Exception as e:
            logger.error(f"Error getting file kind for {self.path}: {e}")
            return 'unknown'

    def __repr__(self):
        return f"<File name={self.name}, size={self.size}B, type={self.type}, kind={self.kind}>"

def get_disassembly(path):
    try:
        return subprocess.check_output(
            ['objdump', '-M', 'intel', '-d', path],
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=5
        )
    except subprocess.TimeoutExpired:
        logger.warning(f"Disassembly timed out for {path}")
        return "Disassembly timed out."
    except FileNotFoundError:
        logger.error("objdump not found. Please install binutils (e.g., `sudo apt install binutils`).")
        return "Disassembly tool (objdump) not found."
    except Exception as e:
        logger.error(f"Disassembly failed for {path}: {e}")
        return f"Disassembly failed: {e}"

def get_strings(path):
    try:
        return subprocess.check_output(
            ['strings', path],
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=3
        )
    except subprocess.TimeoutExpired:
        logger.warning(f"Strings extraction timed out for {path}")
        return "Strings extraction timed out."
    except FileNotFoundError:
        logger.error("strings not found. Please install binutils (e.g., `sudo apt install binutils`).")
        return "Strings tool not found."
    except Exception as e:
        logger.error(f"Strings failed for {path}: {e}")
        return f"Strings failed: {e}"