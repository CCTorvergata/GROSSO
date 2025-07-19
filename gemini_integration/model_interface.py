from rich.console import Console
from typing import Dict, Any, Tuple, Optional

from config import (
    MODELS, TEMPERATURE, TOP_P, TOP_K, REQUEST_TIMEOUT_SECONDS
)
from log_config.logger_config import logger
from api_keys.collector import collect_api_keys
from gemini_client import GeminiClient
from openai_integration.openai_client import OpenAIClient

console = Console()

def get_all_model_responses(file_data: Dict[Any, str], input_dir_name: Optional[str] = None) -> Dict[str, Tuple[Any, str, str]]:
    """
    Connects to various AI models, sends prompts, handles responses, and orchestrates exploit saving.
    This function tries multiple API keys and models until successful responses are received,
    or it collects all available responses.
    """
    all_api_keys = collect_api_keys()  # Collect API keys from environment variables
    
    # This dictionary will store responses from each model
    model_outputs: Dict[str, Tuple[Any, str, str]] = {}

    for provider, model_list in MODELS.items():
        if provider not in all_api_keys or not all_api_keys[provider]:
            logger.warning(f"No API keys found for provider: {provider}. Skipping models for this provider.")
            continue

        api_keys_for_provider = all_api_keys[provider]
        
        # Shuffle API keys to distribute requests
        import random
        random.shuffle(api_keys_for_provider)

        for idx, api_key in enumerate(api_keys_for_provider):
            logger.info(f"Trying API key #{idx + 1} for {provider} models...")
            
            for model_name in model_list:
                logger.info(f"Trying model: {model_name} with API key #{idx + 1} for {provider}")
                
                client: Optional[Any] = None
                try:
                    if provider == "gemini":
                        client = GeminiClient(api_key=api_key, model_name=model_name, config={
                            "temperature": TEMPERATURE, "top_p": TOP_P, "top_k": TOP_K,
                            "request_timeout_seconds": REQUEST_TIMEOUT_SECONDS
                        })
                    elif provider == "openai":
                        client = OpenAIClient(api_key=api_key, model_name=model_name, config={
                            "temperature": TEMPERATURE, "top_p": TOP_P, "top_k": TOP_K,
                            "request_timeout_seconds": REQUEST_TIMEOUT_SECONDS
                        })
                    else:
                        logger.warning(f"Unknown provider: {provider}. Skipping.")
                        continue

                    # Set input directory name for client, if applicable (used for filename generation)
                    if input_dir_name and hasattr(client, '_input_dir_name'):
                        client._input_dir_name = input_dir_name

                    # Use client's own get_model_response
                    chat_session, vuln_text, exploit_text = client.get_model_response(file_data, REQUEST_TIMEOUT_SECONDS)
                    
                    # Store response, keyed by model name
                    model_outputs[model_name] = (chat_session, vuln_text, exploit_text)
                    logger.info(f"Successfully received response from {model_name}.")
                    # Break from model_list loop and API key loop if successful for this provider
                    break 
                except TimeoutError as te:
                    logger.error(f"Model {model_name} with API key #{idx + 1} timed out: {te}")
                    continue
                except RuntimeError as re:
                    logger.error(f"Model {model_name} with API key #{idx + 1} failed with runtime error: {re}")
                    if "Quota o limite di richieste esaurito" in str(re):
                        logger.warning(f"Quota exceeded for API key #{idx + 1} for {provider}. Trying next key.")
                        break # Break from model_list loop to try next API key
                    continue
                except Exception as e:
                    logger.error(f"Model {model_name} with API key #{idx + 1} failed: {e}")
                    continue
            else: # This else belongs to the inner for loop (for model_name in model_list)
                continue # If inner loop completed without break (all models for this key failed), continue to next API key
            break # This break belongs to the outer for loop (for idx, api_key in enumerate(api_keys_for_provider))

    if not model_outputs:
        raise RuntimeError("All API keys and models failed. See logs for details.")
    
    return model_outputs

def get_current_exploit_code():
    """
    This function is now deprecated as exploit code is managed within client classes.
    It's left as a placeholder if a global access point is absolutely required,
    but the primary saving mechanism is in client.
    """
    logger.warning("get_current_exploit_code() is deprecated. Exploit code is saved by the client classes.")
    return None # Or raise an error, depending on desired behavior.