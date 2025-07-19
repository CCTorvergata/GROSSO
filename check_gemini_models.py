import os
from google.generativeai.client import configure as google_configure
from google.generativeai.models import list_models as google_list_models
from dotenv import load_dotenv
import openai
import logging

# Basic logging for this script
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger()

load_dotenv()  # Load environment variables from .env file

# --- Google Gemini ---
google_api_key = os.getenv("GOOGLE_API_KEY")
if not google_api_key:
    logger.error("GOOGLE_API_KEY not found in environment variables or .env file.")
else:
    try:
        google_configure(api_key=google_api_key)
        logger.info("Attempting to list available Gemini models...")
        for m in google_list_models():
            if 'generateContent' in m.supported_generation_methods:
                logger.info(f"  Gemini model: {m.name} (supports generateContent)")
            else:
                logger.info(f"  Gemini model: {m.name} (DOES NOT support generateContent)")
    except Exception as e:
        logger.error(f"Error listing Gemini models: {e}")

# --- OpenAI ---
openai_api_key = os.getenv("OPENAI_API_KEY")
if not openai_api_key:
    logger.error("OPENAI_API_KEY not found in environment variables or .env file.")
else:
    try:
        openai.api_key = openai_api_key
        logger.info("Attempting to list available OpenAI models...")
        models = openai.models.list()
        for m in models:
            logger.info(f"  OpenAI model: {m.id}")
    except Exception as e:
        logger.error(f"Error listing OpenAI models: {e}")