from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from log_config.logger_config import logger
from config import EXPLOIT_TEMPLATE_PATH

class BaseModel(ABC):
    """Abstract base class for AI model integrations."""

    def __init__(self, api_key: str, model_name: str, config: Dict[str, Any]):
        self.api_key = api_key
        self.model_name = model_name
        self.config = config
        self._chat_session = None
        self._exploit_prompt = self._load_exploit_prompts() # Load once per instance
        self._exploit_code_latest: Optional[str] = None
        self._latest_vuln_text: Optional[str] = None
        self._latest_vuln_name: Optional[str] = None
        self._input_dir_name: Optional[str] = None

    def _load_exploit_prompts(self) -> str:
        """Loads exploit prompt templates from files."""
        prompt = "Now, generate a complete exploit code for the identified vulnerabilities. The exploit should be fully functional and ready to run. Prefer Python with the 'pwntools' library for network interactions and exploitation primitives, if applicable.\n\n"
        try:
            with open(EXPLOIT_TEMPLATE_PATH, "r") as f:
                prompt += f.read()
        except FileNotFoundError:
            logger.warning(f"Warning: {EXPLOIT_TEMPLATE_PATH} not found. Exploit prompt might be incomplete.")
        return prompt

    @abstractmethod
    def start_chat(self, history: List[Dict[str, Any]]):
        """Starts a new chat session with the model."""
        pass

    @abstractmethod
    def send_message(self, message: str, timeout: Optional[int] = None) -> Any:
        """Sends a message to the chat session and returns the response."""
        pass

    @abstractmethod
    def prepare_history(self, file_data: Dict[Any, str]) -> List[Dict[str, Any]]:
        """Prepares the chat history for the model based on file data."""
        pass

    @abstractmethod
    def extract_code(self, response: Any) -> str:
        """Extracts code blocks from the model's response."""
        pass
    
    @abstractmethod
    def get_latest_exploit_code(self) -> str:
        """
        Returns the most recently extracted exploit code from the model's responses.
        This method must be implemented by concrete model clients.
        """
        pass

    @abstractmethod
    def get_model_response(self, file_data: Dict[Any, str], timeout: int) -> Any:
        """
        Orchestrates the entire process of getting vulnerability analysis and exploit
        from the model, handling API keys and model selection.
        """
        pass