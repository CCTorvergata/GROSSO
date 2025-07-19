from cli import parse_args
from collector import read_directory_recursively, collect_file_contents
from api_keys.collector import collect_api_keys
from gemini_integration.gemini_client import GeminiClient
from openai_integration.openai_client import OpenAIClient
from model_integration.base_model import BaseModel
from log_config.logger_config import logger
from config import MODELS, TEMPERATURE, TOP_P, TOP_K, REQUEST_TIMEOUT_SECONDS, MERGE_PROMPT_TEMPLATE
import random
import os
from typing import List, Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

# Import Rich per la formattazione della console
from rich.console import Console
from rich.syntax import Syntax

# Importa la funzione per l'interazione dal tuo file
from ui.chat_interface import start_interactive_chat 

# Inizializza la console Rich globalmente o passala
console = Console()

# Helper function to encapsulate model initialization and initial response fetching
def _get_initial_model_responses_parallel(
    all_api_keys: Dict[str, List[str]],
    file_data: Dict[Any, str],
    model_config: Dict[str, Any],
    timeout: int,
    input_dir_name: str # Nuovo parametro
) -> List[Dict[str, Any]]:
    """
    Attempts to get initial vulnerability analysis and exploit from all configured models concurrently.
    Returns a list of dictionaries, each containing model_instance, chat_session,
    provider, model_name, vuln_text, exploit_text.
    """
    
    futures = []
    results = []
    
    with ThreadPoolExecutor(max_workers=len(MODELS) * max(len(keys) for keys in all_api_keys.values()) if all_api_keys else 1) as executor:
        for provider, model_list in MODELS.items():
            if provider not in all_api_keys or not all_api_keys[provider]:
                logger.warning(f"No API keys found for provider: {provider}. Skipping models for this provider.")
                continue

            api_keys_for_provider = all_api_keys[provider]
            random.shuffle(api_keys_for_provider) # Shuffle to distribute load

            for api_key in api_keys_for_provider:
                for model_name in model_list:
                    # Submit task to the thread pool
                    futures.append(executor.submit(_call_model_for_initial_response, 
                                                   provider, model_name, api_key, file_data, model_config, timeout, input_dir_name))
        
        for future in as_completed(futures):
            try:
                result = future.result()
                if result:
                    results.append(result)
            except Exception as e:
                logger.error(f"Error during parallel model response fetching: {e}")
    return results

def _call_model_for_initial_response(
    provider: str,
    model_name: str,
    api_key: str,
    file_data: Dict[Any, str],
    model_config: Dict[str, Any],
    timeout: int,
    input_dir_name: str
) -> Optional[Dict[str, Any]]:
    """Helper function to call a single model and return its initial responses."""
    client: Optional[BaseModel] = None
    try:
        if provider == "gemini":
            client = GeminiClient(api_key=api_key, model_name=model_name, config=model_config)
        elif provider == "openai":
            client = OpenAIClient(api_key=api_key, model_name=model_name, config=model_config)
        else:
            logger.warning(f"Unknown provider: {provider}. Skipping model {model_name}.")
            return None

        # Set input directory name for client for filename generation
        if hasattr(client, '_input_dir_name'):
            client._input_dir_name = input_dir_name

        logger.info(f"Initiating call to {provider} model: {model_name}")
        chat_session, vuln_text, exploit_text = client.get_model_response(file_data, timeout)

        return {
            "model_instance": client,
            "chat_session": chat_session,
            "provider": provider,
            "model_name": model_name,
            "vuln_text": vuln_text,
            "exploit_text": exploit_text,
        }
    except TimeoutError:
        logger.error(f"Model {model_name} timed out after {timeout} seconds.")
        return None
    except Exception as e:
        logger.error(f"Error calling {model_name} from {provider}: {e}")
        return None

def main():
    """Main function to run the CTF exploit generation process."""
    # --- Banner ---
    console.print("[bold green]##########################################[/bold green]")
    console.print("[bold green]#                                        #[/bold green]")
    console.print("[bold green]#        CTF Exploit Generator           #[/bold green]")
    console.print("[bold green]#                                        #[/bold green]")
    console.print("[bold green]#   Powered by Gemini & OpenAI Models    #[/bold green]")
    console.print("[bold green]#                                        #[/bold green]")
    console.print("[bold green]##########################################[/bold green]")
    console.print("\n")


    args = parse_args()

    input_path = args.path
    if not os.path.exists(input_path):
        console.print(f"[bold red]Error:[/bold red] Il percorso specificato '{input_path}' non esiste.")
        return

    input_dir_name = os.path.basename(os.path.abspath(input_path)) if os.path.isdir(input_path) else "unknown_dir"

    # Collezione dei file
    console.print(f"[bold blue]Step 1:[/bold blue] Raccolta dei file da [cyan]{input_path}[/cyan]...")
    try:
        if os.path.isdir(input_path):
            directory_tree = read_directory_recursively(input_path, args.maxsize * 1024)
            file_contents = collect_file_contents(directory_tree)
        elif os.path.isfile(input_path):
            with open(input_path, 'r') as f:
                file_contents = {input_path: f.read()}
        else:
            console.print("[bold red]Error:[/bold red] Il percorso specificato non è né un file né una directory valida.")
            return
        logger.info(f"Collected {len(file_contents)} files.")
        console.print(f"[bold green]Success:[/bold green] Raccolti {len(file_contents)} file.")
    except Exception as e:
        logger.critical(f"Failed to collect files: {e}", exc_info=True)
        console.print(f"[bold red]ERROR:[/bold red] Impossibile raccogliere i file: [red]{e}[/red]")
        return

    if not file_contents:
        console.print("[bold yellow]Attenzione:[/bold yellow] Nessun contenuto file raccolto. Uscita.")
        return

    # Inizializzazione e chiamata ai modelli
    console.print(f"[bold blue]Step 2:[/bold blue] Richiesta analisi delle vulnerabilità e generazione exploit dai modelli AI...")
    model_config = {
        "temperature": TEMPERATURE,
        "top_p": TOP_P,
        "top_k": TOP_K,
        "request_timeout_seconds": REQUEST_TIMEOUT_SECONDS
    }

    initial_responses = _get_initial_model_responses_parallel(
        all_api_keys=collect_api_keys(),
        file_data=file_contents,
        model_config=model_config,
        timeout=REQUEST_TIMEOUT_SECONDS,
        input_dir_name=input_dir_name # Passa il nome della directory
    )

    if not initial_responses:
        console.print("[bold red]ERROR:[/bold red] Nessuna risposta valida ricevuta da nessun modello. Controlla le tue API keys e la connessione.")
        logger.critical("No valid responses received from any model after initial attempts.")
        return

    # Preparazione per la fusione delle risposte
    all_vulnerability_analyses = []
    all_exploit_codes = []
    
    # Track the best model for interactive chat and final saving
    selected_chat_session = None
    final_model_instance = None
    selected_provider = None
    selected_model_name = None

    for res in initial_responses:
        all_vulnerability_analyses.append(f"--- Analisi da {res['provider']} ({res['model_name']}) ---\n{res['vuln_text']}\n")
        # Exploit code from initial responses are directly saved by the client.
        # We will re-generate a merged exploit later.

        # Pick the first successful model for interactive chat
        if selected_chat_session is None and res['chat_session'] is not None:
            selected_chat_session = res['chat_session']
            final_model_instance = res['model_instance']
            selected_provider = res['provider']
            selected_model_name = res['model_name']
            logger.info(f"Selected {selected_model_name} from {selected_provider} for interactive chat and final merging.")


    # Unione delle analisi e richiesta dell'exploit finale
    console.print(f"[bold blue]Step 3:[/bold blue] Unione delle analisi e richiesta dell'exploit consolidato...")
    
    if final_model_instance is None:
        console.print("[bold red]ERROR:[/bold red] Nessun modello disponibile per la fase di merge e generazione exploit finale.")
        logger.critical("No model instance selected for final merge and exploit generation.")
        return

    try:
        # Costruisci il prompt di merge con tutte le analisi raccolte
        full_merge_prompt = MERGE_PROMPT_TEMPLATE.format(all_vulnerability_analyses="\n".join(all_vulnerability_analyses))
        
        # Invia il prompt di merge al modello selezionato
        logger.info(f"Requesting merged exploit from {selected_provider} ({selected_model_name})...")
        merge_response_obj = final_model_instance.send_message(full_merge_prompt, timeout=REQUEST_TIMEOUT_SECONDS)

        final_merged_exploit_code = ""
        if merge_response_obj and hasattr(merge_response_obj, "text"):
            merged_response_text = merge_response_obj.text.strip()
            console.print(f"[bold cyan]Final Merged Exploit from {selected_provider} ({selected_model_name}):[/bold cyan]")
            syntax = Syntax(merged_response_text, "python", theme="one-dark", line_numbers=True)
            console.print(syntax)
            
            # Extract and save the final exploit code
            final_merged_exploit_code = final_model_instance.extract_code(merge_response_obj)
            
            # Pass input_dir_name to _save_exploit_code for proper naming
            if hasattr(final_model_instance, '_input_dir_name'):
                final_model_instance._input_dir_name = input_dir_name
            
            # Save the final merged exploit code
            final_model_instance._save_exploit_code(final_merged_exploit_code)
        else:
            logger.warning("No exploit code was generated from the merged analysis (possibly due to quota).")
            console.print("[red]Warning: No exploit code was generated from the merged analysis (possibly due to quota).[/red]")
        
    except Exception as e:
        logger.critical(f"Failed to generate merged exploit with {selected_provider} ({selected_model_name}): {e}", exc_info=True)
        console.print(f"[bold red]ERROR:[/bold red] Failed to generate merged exploit: [red]{e}[/red]")
        return

    logger.info("Process completed. Check the console for the final merged exploit code.")
    console.print("[bold green]Process completed. Final exploit code displayed above and saved to file.[/bold green]")
    
    # --- Start Interactive Chat ---
    # Solo se abbiamo un'istanza del modello e una sessione di chat valide
    if selected_chat_session and final_model_instance:
        console.print("\n[bold magenta]--- Starting Interactive Chat with the AI Model ---[/bold magenta]")
        console.print("[bold magenta]Type 'exit' or 'quit' to leave. Press Ctrl+X to copy the latest exploit.[/bold magenta]")
        start_interactive_chat(selected_chat_session, final_model_instance)
    else:
        console.print("[yellow]Cannot start interactive chat: model session or instance not available.[/yellow]")


if __name__ == "__main__":
    main()