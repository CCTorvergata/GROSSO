import openai
import multiprocessing
import os
import hashlib
import re
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime

from openai.types.chat import ChatCompletionMessageParam, ChatCompletionUserMessageParam, ChatCompletionAssistantMessageParam
from openai import APIStatusError

from model_integration.base_model import BaseModel
from log_config.logger_config import logger
from config import (
    CONTEXT_PROMPT, VULNS_PROMPT, RESPONSES, REQUEST_TIMEOUT_SECONDS,
    TEMPERATURE, TOP_P, TOP_K, EXPLOIT_DIR,
    EXPLOIT_FILENAME_PREFIX, EXPLOIT_FILENAME_SUFFIX
)
from utils.file_utils import extract_code_from_response
from rich.console import Console
from rich.markdown import Markdown

console = Console()

class MockResponse:
    def __init__(self, text: str):
        self.text = text

class OpenAIClient(BaseModel):
    """Concrete implementation of BaseModel for OpenAI models (ChatGPT)."""

    def __init__(self, api_key: str, model_name: str, config: Dict[str, Any]):
        super().__init__(api_key, model_name, config)
        self._exploit_code_latest: Optional[str] = None
        self._client = openai.OpenAI(api_key=self.api_key)
        self._chat_session_history: List[Dict[str, Any]] = []
        self._latest_vuln_text: Optional[str] = None

    def start_chat(self, history: List[Dict[str, Any]]) -> Any:
        self._chat_session_history = history
        logger.info(f"OpenAI chat session initialized for model: {self.model_name}")
        return self

    def _send_message_worker(
        self,
        messages: List[ChatCompletionMessageParam],
        model_name: str,
        config: Dict[str, Any],
        return_dict: Dict[str, Any]
    ):
        try:
            response = self._client.chat.completions.create(
                model=model_name,
                messages=messages,
                temperature=config.get('temperature', TEMPERATURE),
                top_p=config.get('top_p', TOP_P),
            )
            return_dict["response_obj"] = response
            if response.choices and response.choices[0].message.content:
                return_dict["response_text"] = response.choices[0].message.content
        except APIStatusError as e:
            if e.status_code == 429:
                return_dict["error"] = f"APIStatusError 429: {e.response}"
                return_dict["is_quota_error"] = True
            else:
                return_dict["error"] = str(e)
        except Exception as e:
            return_dict["error"] = str(e)

    def send_message(self, message: str, timeout: Optional[int] = None) -> Any:
        if not hasattr(self, '_chat_session_history'):
            raise RuntimeError("Chat session not started. Call start_chat() first.")

        user_message: ChatCompletionUserMessageParam = {"role": "user", "content": message}
        self._chat_session_history.append(dict(user_message))

        manager = multiprocessing.Manager()
        return_dict = manager.dict()
        
        effective_timeout = timeout if timeout is not None else self.config.get('request_timeout_seconds', REQUEST_TIMEOUT_SECONDS)

        messages_for_api: List[Dict[str, Any]] = list(self._chat_session_history)

        process = multiprocessing.Process(
            target=self._send_message_worker,
            args=(messages_for_api, self.model_name, self.config, return_dict)
        )
        process.start()
        process.join(effective_timeout)

        if process.is_alive():
            process.terminate()
            process.join()
            logger.warning(f"OpenAI send_message() timed out after {effective_timeout} seconds.")
            raise TimeoutError(f"OpenAI send_message() timed out after {effective_timeout} seconds")

        if "error" in return_dict:
            if return_dict.get("is_quota_error"):
                # Qui gestiamo l'errore 429 in modo "gentile"
                logger.error(f"OpenAI ({self.model_name}): Quota o limite di richieste esaurito per l'API Key corrente. Dettagli: {return_dict['error']}")
                return None # Restituisce None per indicare il fallimento a causa della quota
            else:
                raise RuntimeError(f"OpenAI send_message() failed: {return_dict['error']}")

        model_response_content = return_dict.get("response_text")

        if model_response_content:
            assistant_message: ChatCompletionAssistantMessageParam = {"role": "assistant", "content": model_response_content}
            self._chat_session_history.append(dict(assistant_message))
            return MockResponse(model_response_content)
        else:
            logger.warning("No response content received from OpenAI model.")
            return MockResponse("(No response content received from OpenAI)")

    def prepare_history(self, file_data: Dict[Any, str]) -> List[Dict[str, Any]]:
        history: List[Dict[str, Any]] = [
            {"role": "system", "content": CONTEXT_PROMPT},
            {"role": "assistant", "content": (
            "I understand. I'm ready to analyze code for CTF vulnerabilities and create exploits. "
            "Please provide the files you'd like me to examine."
            )}
        ]
        for i, (file_obj, content) in enumerate(file_data.items()):
            file_name = getattr(file_obj, "name", str(file_obj))
            logger.debug(f"Adding file '{file_name}' to OpenAI history.")
            user_msg: ChatCompletionUserMessageParam = {"role": "user", "content": f"File: {file_name}\n\n```\n{content}\n```"}
            assistant_msg: ChatCompletionAssistantMessageParam = {"role": "assistant", "content": RESPONSES[i % len(RESPONSES)].format(file_name)}
            history.extend([dict(user_msg), dict(assistant_msg)])
        return history

    def extract_code(self, response: Any) -> str:
        response_text = getattr(response, "text", "")
        extracted_code = extract_code_from_response(response_text)
        self._exploit_code_latest = extracted_code
        logger.debug(f"Extracted code from OpenAI response. Length: {len(self._exploit_code_latest)} chars.")
        return extracted_code

    def get_latest_exploit_code(self) -> str:
        return self._exploit_code_latest if self._exploit_code_latest is not None else ""

    def _save_exploit_code(self, code_content: str) -> Optional[str]:
        """Saves the exploit code to a uniquely named Python file in the 'exploits' directory."""
        if not code_content:
            logger.warning("No exploit code content to save for OpenAI.")
            return None

        # Crea la cartella 'exploits' se non esiste
        os.makedirs(EXPLOIT_DIR, exist_ok=True)

        # Genera un timestamp per l'unicità
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        # Prepara il nome della vulnerabilità pulito
        vuln_desc = "unknown_vuln"  # Default value
        if self._latest_vuln_text:
            # Try to extract the concise vulnerability name from the text
            match = re.search(r"Sintesi Vulnerabilità:\s*\[(.*?)\]", self._latest_vuln_text, re.IGNORECASE)
            if match:
                extracted_name = match.group(1).strip()
                vuln_desc = re.sub(r'[^\w\s-]', '', extracted_name).strip()
                vuln_desc = re.sub(r'[-\s]+', '_', vuln_desc)
            else:
                # Fallback to a short hash if no clear vulnerability name is found
                vuln_desc = hashlib.sha256(self._latest_vuln_text.encode()).hexdigest()[:8]

        # Costruisci il nome del file finale
        # Formato desiderato: exploit_<name_of_vuln>_<timestamp>.py
        filename = f"{EXPLOIT_FILENAME_PREFIX}{vuln_desc}_{timestamp}{EXPLOIT_FILENAME_SUFFIX}"
        
        full_path = os.path.join(EXPLOIT_DIR, filename)

        try:
            with open(full_path, "w") as f:
                f.write(code_content)
            logger.info(f"Exploit saved to {full_path}")
            return full_path
        except Exception as e:
            logger.error(f"Failed to save exploit to {full_path}: {e}")
            return None

    def get_model_response(self, file_data: Dict[Any, str], timeout: int) -> Tuple[Any, str, str]:
        initial_history = self.prepare_history(file_data)
        chat_session_obj = self.start_chat(history=initial_history)

        logger.info(f"Requesting vulnerabilities analysis from OpenAI ({self.model_name})...")
        response_vulns_obj = self.send_message(VULNS_PROMPT, timeout=timeout)

        vuln_text = ""
        if response_vulns_obj and hasattr(response_vulns_obj, "text"):
            vuln_text = response_vulns_obj.text.strip()
            self._latest_vuln_text = vuln_text # Save the latest vulnerability analysis text
            console.print(f"[bold yellow]OpenAI ({self.model_name}) - Vulnerabilities:[/bold yellow]")
            console.print(Markdown(f"{vuln_text}"))
        else:
            logger.warning(f"OpenAI ({self.model_name}): No response or invalid response received for vulnerabilities analysis.")
            # Se la richiesta di vulnerabilità fallisce per quota, non tentare l'exploit con lo stesso modello
            if response_vulns_obj is None: # Se send_message ha restituito None a causa di quota
                return chat_session_obj, "", "" # Restituisce stringhe vuote per indicare fallimento

        logger.info(f"Requesting initial exploit code generation from OpenAI ({self.model_name})...")
        response_exploit_obj = self.send_message(self._exploit_prompt, timeout=timeout)
        
        exploit_text = ""
        if response_exploit_obj and hasattr(response_exploit_obj, "text"):
            exploit_text = response_exploit_obj.text.strip()
            console.print(f"[bold green]OpenAI ({self.model_name}) - Initial Exploit:[/bold green]")
            console.print(Markdown(f"{exploit_text}"))
            self.extract_code(response_exploit_obj)
            self._save_exploit_code(self._exploit_code_latest or "")
        else:
            logger.warning(f"OpenAI ({self.model_name}): No response or invalid response received for initial exploit.")
            if response_exploit_obj is None: # Se send_message ha restituito None a causa di quota
                return chat_session_obj, vuln_text, ""

        return chat_session_obj, vuln_text, exploit_text