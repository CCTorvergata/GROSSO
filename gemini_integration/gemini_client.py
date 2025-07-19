from google.generativeai.client import configure
from google.generativeai.generative_models import GenerativeModel
from google.generativeai.types import GenerationConfig
from google.generativeai.types import ContentDict
import os
import hashlib
import multiprocessing
import re
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime

from model_integration.base_model import BaseModel
from log_config.logger_config import logger
from config import (
    CONTEXT_PROMPT, VULNS_PROMPT, EXPLOIT_TEMPLATE_PATH,
    RESPONSES, TEMPERATURE, TOP_P, TOP_K, REQUEST_TIMEOUT_SECONDS, EXPLOIT_DIR,
    EXPLOIT_FILENAME_PREFIX, EXPLOIT_FILENAME_SUFFIX
)
from rich.console import Console
from rich.markdown import Markdown

console = Console()

class GeminiClient(BaseModel):
    """Concrete implementation of BaseModel for Google Gemini."""

    def __init__(self, api_key: str, model_name: str, config: Dict[str, Any]):
        super().__init__(api_key, model_name, config)
        
        self._exploit_prompt = self._load_exploit_prompt_from_file(EXPLOIT_TEMPLATE_PATH)
        
        configure(api_key=self.api_key)
    
    def _extract_vuln_name_from_response(self, vuln_analysis_text: str) -> str:
        """
        Tenta di estrarre il nome conciso della vulnerabilità dall'analisi.
        Cerca la riga "Sintesi Vulnerabilità: [Nome]"
        """
        match = re.search(r"Sintesi Vulnerabilità:\s*\[(.*?)\]", vuln_analysis_text, re.IGNORECASE)
        if match:
            extracted_name = match.group(1).strip()
            # Pulisci il nome per usarlo in un nome file
            cleaned_name = re.sub(r'[^\w\s-]', '', extracted_name) # Rimuovi caratteri non validi
            cleaned_name = re.sub(r'[-\s]+', '_', cleaned_name)    # Rimpiazza spazi e trattini con underscore
            return cleaned_name
        return ""

    def _load_exploit_prompt_from_file(self, file_path: str) -> str:
        """Loads exploit prompt template from a file."""
        prompt = "Now, generate a complete exploit code for the identified vulnerabilities. The exploit should be fully functional and ready to run. Prefer Python with the 'pwntools' library for network interactions and exploitation primitives, if applicable.\n\n"
        try:
            with open(file_path, "r") as f:
                prompt += f.read()
            logger.debug(f"Loaded exploit prompt from {file_path}")
        except FileNotFoundError:
            logger.warning(f"Warning: Exploit prompt template file '{file_path}' not found. Exploit prompt might be incomplete.")
        return prompt

    def start_chat(self, history: List[Dict[str, Any]]) -> Any:
        """Starts a new chat session with the Gemini model."""
        try:
            self._model = GenerativeModel(
                model_name=self.model_name,
                generation_config=GenerationConfig(
                    temperature=self.config.get('temperature', TEMPERATURE),
                    top_p=self.config.get('top_p', TOP_P),
                    top_k=self.config.get('top_k', TOP_K)
                ),
            )
            strict_history = [ContentDict(**entry) for entry in history]
            self._chat_session = self._model.start_chat(history=strict_history)
            logger.info(f"Gemini chat session started with model: {self.model_name}")
            return self._chat_session
        except Exception as e:
            logger.error(f"Failed to start chat session with {self.model_name}: {e}")
            raise

    def _send_message_worker(self, chat_session_instance: Any, message: str, return_dict: Dict[str, Any]):
        """Worker function for sending messages with multiprocessing."""
        try:
            response = chat_session_instance.send_message(message)
            return_dict["response_obj"] = response # Store full object for extract_code
        except Exception as e:
            return_dict["error"] = str(e)

    def send_message(self, message: str, timeout: Optional[int] = None) -> Any:
        """
        Sends a message to the chat session with an optional timeout.
        Uses multiprocessing to enforce the timeout.
        """
        if not self._chat_session:
            raise RuntimeError("Chat session not started. Call start_chat() first.")

        manager = multiprocessing.Manager()
        return_dict = manager.dict()
        
        effective_timeout = timeout if timeout is not None else self.config.get('request_timeout_seconds', REQUEST_TIMEOUT_SECONDS)

        process = multiprocessing.Process(target=self._send_message_worker, args=(self._chat_session, message, return_dict))
        process.start()
        process.join(effective_timeout)

        if process.is_alive():
            process.terminate()
            process.join()
            logger.warning(f"Gemini send_message() timed out after {effective_timeout} seconds.")
            raise TimeoutError(f"Gemini send_message() timed out after {effective_timeout} seconds")

        if "error" in return_dict:
            logger.error(f"Gemini send_message() failed: {return_dict['error']}")
            raise RuntimeError(f"Gemini send_message() failed: {return_dict['error']}")

        response_obj = return_dict.get("response_obj")
        return response_obj

    def prepare_history(self, file_data: Dict[Any, str]) -> List[Dict[str, Any]]:
        """
        Prepares the chat history for the Gemini model based on provided file data.
        """
        history = [
            {"role": "user", "parts": [{"text": CONTEXT_PROMPT}]},
            {"role": "model", "parts": [{"text": (
                "I understand. I'm ready to analyze code for CTF vulnerabilities and create exploits. "
                "Please provide the files you'd like me to examine."
            )}]},
        ]

        for i, (file_obj, content) in enumerate(file_data.items()):
            file_name = getattr(file_obj, "name", str(file_obj))
            logger.debug(f"Adding file '{file_name}' to Gemini history.")
            history.extend([
                {"role": "user", "parts": [{"text": f"File: {file_name}\n\n```\n{content}\n```"}]},
                {"role": "model", "parts": [{"text": RESPONSES[i % len(RESPONSES)].format(file_name)}]}
            ])
        return history

    def extract_code(self, response: Any) -> str:
        """
        Extracts code blocks from a model's response.
        Assumes code is within markdown triple backticks.
        Prioritizes Python blocks, then any generic code block.
        """
        if not hasattr(response, 'text') or not response.text:
            logger.debug("No text in Gemini response to extract code from.")
            return ""
        
        # Try to find Python code blocks first
        python_code_blocks = re.findall(r"```python\s*(.*?)\s*```", response.text, re.DOTALL)
        if python_code_blocks:
            self._exploit_code_latest = python_code_blocks[-1].strip()
            logger.debug(f"Extracted Python code from Gemini response. Length: {len(self._exploit_code_latest) if self._exploit_code_latest is not None else 0} chars.")
            return self._exploit_code_latest if self._exploit_code_latest is not None else ""

        # If no Python specific block, find any generic code block
        generic_code_blocks = re.findall(r"```(?:[a-zA-Z0-9]*)\s*(.*?)\s*```", response.text, re.DOTALL)
        if generic_code_blocks:
            self._exploit_code_latest = generic_code_blocks[-1].strip()
            logger.debug(f"Extracted generic code from Gemini response. Length: {len(self._exploit_code_latest) if self._exploit_code_latest is not None else 0} chars.")
            return self._exploit_code_latest if self._exploit_code_latest is not None else ""
            
        # As a fallback, return the entire response text if no code blocks found
        self._exploit_code_latest = response.text.strip()
        logger.debug("No code blocks found in Gemini response, returning full text as fallback.")
        return self._exploit_code_latest if self._exploit_code_latest is not None else ""

    def get_latest_exploit_code(self) -> str:
        """Returns the most recently extracted exploit code."""
        return self._exploit_code_latest if self._exploit_code_latest is not None else ""

    def _save_exploit_code(self, code_content: str) -> Optional[str]:
        """Saves the exploit code to a uniquely named Python file in the 'exploits' directory."""
        if not code_content:
            logger.warning(f"No exploit code content to save for {self.model_name}.")
            return None

        # Crea la cartella 'exploits' se non esiste
        os.makedirs(EXPLOIT_DIR, exist_ok=True)

        # Prepara il nome della vulnerabilità pulito
        vuln_name_part = "unknown_vuln"
        if self._latest_vuln_name:
            vuln_name_part = self._latest_vuln_name
        elif self._latest_vuln_text: # Fallback se _latest_vuln_name non è stato estratto
            extracted_fallback_name = self._extract_vuln_name_from_response(self._latest_vuln_text)
            if extracted_fallback_name:
                vuln_name_part = extracted_fallback_name
            else:
                # Se non riusciamo a estrarre nulla di significativo dal testo, usiamo un hash
                vuln_name_part = hashlib.sha256(self._latest_vuln_text.encode()).hexdigest()[:8] # Un breve hash

        # Prepara il nome della directory di input
        input_dir_part = "unknown_dir"
        if self._input_dir_name:
            # Pulisci il nome della directory per usarlo in un nome file
            cleaned_dir_name = re.sub(r'[^\w\s-]', '', self._input_dir_name)
            cleaned_dir_name = re.sub(r'[-\s]+', '_', cleaned_dir_name)
            if cleaned_dir_name:
                input_dir_part = cleaned_dir_name

        # Genera un timestamp per l'unicità
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        # Costruisci il nome del file finale
        # Formato desiderato: exploit_<name_of_vuln>_<dir_input_name>_<timestamp>.py
        filename = f"{EXPLOIT_FILENAME_PREFIX}{vuln_name_part}_{input_dir_part}_{timestamp}{EXPLOIT_FILENAME_SUFFIX}"
        
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
        chat = self.start_chat(history=initial_history)

        logger.info(f"Requesting vulnerabilities analysis from {self.model_name}...")
        response_vulns_obj = self.send_message(VULNS_PROMPT, timeout=timeout)

        vuln_text = ""
        if response_vulns_obj is not None and hasattr(response_vulns_obj, "text"):
            vuln_text = response_vulns_obj.text.strip()
            self._latest_vuln_text = vuln_text # Salva l'ultima analisi di vulnerabilità completa
            self._latest_vuln_name = self._extract_vuln_name_from_response(vuln_text) # Estrai il nome conciso
            console.print(Markdown(f"**{self.model_name} - Vulnerabilities:**\n\n{vuln_text}"))
        else:
            logger.warning(f"{self.model_name}: No response or invalid response received for vulnerabilities analysis.")
            if response_vulns_obj is None:
                return chat, "", ""

        logger.info(f"Requesting initial exploit code generation from {self.model_name}...")
        # Per la generazione dell'exploit, potresti voler passare il nome della vulnerabilità se lo ritieni utile
        # per guidare il modello (anche se il MERGE_PROMPT_TEMPLATE è già abbastanza dettagliato).
        response_exploit_obj = self.send_message(self._exploit_prompt, timeout=timeout)

        exploit_text = ""
        if response_exploit_obj is not None and hasattr(response_exploit_obj, "text"):
            exploit_text = response_exploit_obj.text.strip()
            console.print(Markdown(f"**{self.model_name} - Initial Exploit:**\n\n{exploit_text}"))
            self.extract_code(response_exploit_obj)
        else:
            logger.warning(f"{self.model_name}: No response or invalid response received for initial exploit.")
            if response_exploit_obj is None:
                return chat, vuln_text, ""

        return chat, vuln_text, exploit_text