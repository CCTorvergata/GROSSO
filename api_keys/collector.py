import os
from dotenv import load_dotenv
from config import DEFAULT_API_KEY_COUNT
from log_config.logger_config import logger

def collect_api_keys(num_api_keys=DEFAULT_API_KEY_COUNT):
    """
    Collects API keys from environment variables.
    Looks for GOOGLE_API_KEY, OPENAI_API_KEY, and then numbered variants.
    """
    load_dotenv()
    api_keys = {}

    # Collect Google API Keys
    google_keys = set()
    main_google_key = os.getenv("GOOGLE_API_KEY")
    if main_google_key:
        google_keys.add(main_google_key)
        logger.debug("Found standard GOOGLE_API_KEY.")
    for i in range(1, num_api_keys + 1):
        key = os.getenv(f"GOOGLE_API_KEY_{i}")
        if key:
            google_keys.add(key)
            logger.debug(f"Found numbered GOOGLE_API_KEY_{i}.")
    if google_keys:
        api_keys["gemini"] = list(google_keys)
    else:
        logger.debug("No Google API keys found.")

    # Collect OpenAI API Keys
    openai_keys = set()
    main_openai_key = os.getenv("OPENAI_API_KEY")
    if main_openai_key:
        openai_keys.add(main_openai_key)
        logger.debug("Found standard OPENAI_API_KEY.")
    for i in range(1, num_api_keys + 1):
        key = os.getenv(f"OPENAI_API_KEY_{i}")
        if key:
            openai_keys.add(key)
            logger.debug(f"Found numbered OPENAI_API_KEY_{i}.")
    if openai_keys:
        api_keys["openai"] = list(openai_keys)
    else:
        logger.debug("No OpenAI API keys found.")

    # You could add a check here to ensure at least one provider has keys
    if not api_keys:
        logger.warning("No API keys found for any provider. Please set them in your environment or .env file.")

    return api_keys