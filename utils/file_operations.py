import re
from utils.logger import logger
from config import EXPLOIT_FILENAME_PREFIX, EXPLOIT_FILENAME_SUFFIX
from datetime import datetime

def extract_exploit_code(response):
    """
    Extracts code blocks from a model's response.
    Assumes code is within markdown triple backticks.
    """
    if not hasattr(response, 'text') or not response.text:
        return None
    
    # Regex to find code blocks marked with ```python or just ```
    # It's more robust to also capture code without a language specified.
    code_blocks = re.findall(r"```(?:python)?\s*(.*?)\s*```", response.text, re.DOTALL)
    
    if code_blocks:
        # Return the first found code block
        return code_blocks[0].strip()
    return None

def save_exploit_code(code_content):
    """
    Saves the exploit code to a uniquely named Python file.
    """
    if not code_content:
        logger.warning("No exploit code content to save.")
        return None

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{EXPLOIT_FILENAME_PREFIX}{timestamp}{EXPLOIT_FILENAME_SUFFIX}"
    try:
        with open(filename, "w") as f:
            f.write(code_content)
        logger.info(f"Exploit saved to {filename}")
        return filename
    except Exception as e:
        logger.error(f"Failed to save exploit to {filename}: {e}")
        return None