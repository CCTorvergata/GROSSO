from file_info import File
import re
from config import EXCLUDE_DIRS # Import from config
from log_config.logger_config import logger # Import the logger

def is_executable_file(file: File) -> bool:
    """Checks if a file's MIME type indicates it's an executable."""
    executable_types = {
        'application/x-executable',
        'application/x-pie-executable',
        'application/x-sharedlib',
        'application/x-mach-binary',
        'application/x-dosexec'
    }
    return file.type in executable_types

def should_collect(file: File, max_size: int) -> bool:
    """
    Determines if a file should be collected based on its kind, size, and path.
    """
    if file.kind == 'directory' or file.size > max_size:
        return False
    
    # Check if any excluded directory substring is in the file's path
    for excl_dir in EXCLUDE_DIRS:
        if excl_dir in file.path:
            # logger.debug(f"Skipping {file.name}: Path contains excluded directory {excl_dir}")
            return False

    if file.kind == 'text':
        return True
        
    return file.kind == 'binary' and is_executable_file(file)

def extract_code_from_response(ai_response_text: str) -> str:
    """
    Extracts the latest code block from a raw AI response string.
    Prioritizes Python code blocks.
    """
    if not ai_response_text:
        return ""
    
    # Try to find Python code blocks first
    python_code_blocks = re.findall(r"```python\s*(.*?)\s*```", ai_response_text, re.DOTALL)
    if python_code_blocks:
        return python_code_blocks[-1].strip() # Return the last Python code block

    # If no Python specific block, find any generic code block
    # This was the line with the typo: 'ai_response_blocks' should be 'ai_response_text'
    generic_code_blocks = re.findall(r"```(?:[a-zA-Z0-9]*)\s*(.*?)\s*```", ai_response_text, re.DOTALL)
    if generic_code_blocks:
        return generic_code_blocks[-1].strip() # Return the last generic code block
        
    return ai_response_text.strip() # Fallback: return the entire text if no code block found