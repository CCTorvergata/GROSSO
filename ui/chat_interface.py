import pyperclip
from prompt_toolkit import PromptSession
from prompt_toolkit.key_binding import KeyBindings
from rich.console import Console
from rich.markdown import Markdown

from log_config.logger_config import logger
from config import COLORS, COLOR_RESET

def multiline_input(prompt="You: ", model_instance=None):
    """
    Handles multiline input from the user, allowing 'Enter' for new lines
    and 'Enter' on an empty line to submit. Also handles Ctrl+X for copying exploit code.
    Accepts model_instance to get current exploit.
    """
    session = PromptSession()
    bindings = KeyBindings()
    
    console = Console() # Usa una console locale per i messaggi quick

    @bindings.add('enter')
    def _(event):
        if not event.app.current_buffer.complete_state:
            event.app.exit(result=event.app.current_buffer.text)

    @bindings.add('escape', 'enter')
    def _(event):
        event.app.current_buffer.insert_text('\n')

    @bindings.add('c-x') # Ctrl+X to copy exploit code
    def _(event):
        if model_instance:
            exploit_code = model_instance.get_latest_exploit_code() # Chiama il metodo del modello
            if exploit_code:
                try:
                    pyperclip.copy(exploit_code)
                    logger.info("Exploit code copied to clipboard.")
                    console.print("[green]Exploit code copied to clipboard![/green]")
                except pyperclip.PyperclipException as e:
                    logger.error(f"Failed to copy to clipboard: {e}. Is xclip/xsel installed (Linux)?")
                    console.print(f"[red]Error copying to clipboard: {e}[/red]")
            else:
                logger.warning("No exploit code to copy yet.")
                console.print("[yellow]No exploit code to copy yet.[/yellow]")
        else:
            logger.warning("Model instance not available for exploit code copy.")
            console.print("[red]Error: Model instance not available for exploit code copy.[/red]")
        # Do not exit the prompt, just perform the action
        event.app.current_buffer.insert_text('') # No visual change but allows binding to work without exiting

    return session.prompt(prompt, multiline=True, key_bindings=bindings)

def start_interactive_chat(chat_session, model_instance):
    """
    Starts an interactive chat session with the selected AI model.
    Assumes model_instance has a send_message method and a get_latest_exploit_code method.
    """
    console = Console()
    info_color = COLORS.get('INFO', '')
    print(f"{info_color}---- Entering interactive mode. Type 'exit', 'quit', or Ctrl+D to leave. ----{COLOR_RESET}")
    print(f"{info_color}---- Press Ctrl+X to copy the latest generated exploit code to clipboard. ----{COLOR_RESET}")
    print(f"{info_color}---- Press Escape+Enter for a new line, Enter on empty line to submit. ----{COLOR_RESET}")

    while True:
        try:
            # Passa l'istanza del modello a multiline_input per abilitare Ctrl+X
            user_input = multiline_input("You: ", model_instance=model_instance).strip()
            
            if user_input.lower() in {"exit", "quit"}:
                console.print(f"{info_color}Exiting chat session. Goodbye!{COLOR_RESET}")
                break

            logger.info(f"Interactive chat user input: {user_input}")
            
            # OpenAI e Gemini usano send_message, che dovrebbe restituire un oggetto con .text
            response_obj = model_instance.send_message(user_input) 
            
            response_text = ""
            if response_obj and hasattr(response_obj, "text"):
                response_text = response_obj.text.strip()
            elif response_obj and isinstance(response_obj, str): # Fallback se restituisce una stringa diretta
                response_text = response_obj.strip()

            if response_text:
                console.print(Markdown(f"**AI Model**: {response_text}", code_theme="one-dark"))
                logger.debug(f"Interactive chat model response: {response_text[:200]}...") # Log parziale

                # Tentativo di estrarre e salvare nuovo codice dall'interazione
                # Nota: questo è un'euristica. I modelli potrebbero non sempre generare codice in ogni risposta interattiva.
                extracted_code = model_instance.extract_code(response_obj)
                if extracted_code and extracted_code != model_instance.get_latest_exploit_code():
                    logger.info("New code block detected in interactive response. Updating latest exploit.")
                    model_instance._save_exploit_code(extracted_code) # Salva il nuovo exploit
            else:
                console.print("[yellow]AI Model: (No response received or response was empty)[/yellow]")
                logger.warning("Interactive chat: No response text received from model.")

        except (KeyboardInterrupt, EOFError): # Ctrl+C or Ctrl+D
            console.print(f"[{COLORS.get('INFO', 'white')}]Exiting chat session. Goodbye![/]", style=COLORS.get('INFO', 'white'))
            break
        except Exception as e:
            logger.error(f"Interactive chat error with {model_instance.model_name}: {e}", exc_info=True)
            console.print(f"[bold red]Error during interactive chat:[/bold red] [red]{e}[/red]")