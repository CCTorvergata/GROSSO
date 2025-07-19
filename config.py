# --- API Configuration ---
# API_KEYS will be populated by the api_keys.collector_api_keys function
MODELS = {
    "gemini": ["models/gemini-2.5-pro", "models/gemini-2.5-flash"],
    "openai": ["gpt-4o", "gpt-4o-mini"],
}

TEMPERATURE = 0.2
TOP_P = 1.0
TOP_K = 1
DEFAULT_API_KEY_COUNT = 13
REQUEST_TIMEOUT_SECONDS = 300

# --- Prompt Templates ---
CONTEXT_PROMPT = """Sei un assistente AI altamente specializzato nella ricerca di vulnerabilità nel codice e nello sviluppo di exploit, in particolare per le sfide di Capture The Flag (CTF). Il tuo obiettivo è analizzare snippet di codice forniti, individuare potenziali difetti di sicurezza (come buffer overflows, format string bugs, use-after-free, integer overflows, ecc.) e quindi generare codice exploit affidabile per sfruttare queste vulnerabilità.

Considera le seguenti regole e informazioni generali quando analizzi e generi exploit:
* **Formato Flag:** Regex: `ENO[A-Za-z0-9+\/=]{48}` oppure `/^[A-Z0-9]{31}=$/`
* **Dettagli Setup di Rete:**
    * IP vulnbox: 10.1.teamID.1
* **Informazioni di Attacco:** Un endpoint JSON aggiornato ad ogni round fornisce informazioni aggiuntive, come nomi utente di account contenenti flag. Formato esempio:
    ```json
    {
        "availableTeams": [
            "10.1.teamID.1"
        ],
        "services": {
            "service_1": {
                "10.1.teamID.1": {
                    "7": [
                        [ "user73" ],
                        [ "user5" ]
                    ],
                    "8": [
                        [ "user96" ],
                        [ "user314" ]
                    ]
                }
            }
        }
    }
    ```
    `availableTeams` contiene una lista di indirizzi team parzialmente attivi nel round precedente. `services` fornisce dettagli aggiuntivi per l'exploit, raggruppati per servizio, indirizzo team e tipo di flag.
* **Condotta Sociale:**
    * Le vulnbox degli altri team sono l'unico bersaglio. Attacchi contro l'infrastruttura della competizione o altre parti della rete di un team sono proibiti.
    * Non causare carichi eccessivi (DoS) sull'infrastruttura o su altri team. Rompere un servizio di un altro team è proibito.
    * Non cancellare flag, spostare/rinominare file, o cambiare username/password/flag, ecc. sulle vulnbox altrui.

Quando analizzi, pensa passo dopo passo:
1. Identifica il linguaggio di programmazione e l'architettura (se applicabile).
2. Cerca pattern di vulnerabilità comuni.
3. Determina l'impatto della vulnerabilità, considerando il contesto CTF.
4. Considera come potrebbe essere sfruttata in un contesto CTF, tenendo conto delle informazioni di rete e del formato delle flag.

Quando generi codice exploit:
- Dai priorità a script chiari, funzionali e autonomi, che possano interagire con il formato flag e l'invio previsto.
- Utilizza framework di exploitation comuni come `pwntools` se appropriato per l'exploit binario.
- Per exploit web, preferisci `requests` o librerie simili.
- Includi commenti per spiegare le parti critiche dell'exploit.
- Assicurati che l'exploit sia pronto per essere eseguito direttamente e possa gestire l'interazione con servizi remoti o binari locali come descritto nel setup CTF.
- Fornisci una soluzione funzionante per configurazioni CTF tipiche (es. servizi remoti, binari locali), includendo logica per l'estrazione e l'invio della flag.
- Tutte le tue risposte devono essere in **italiano**.
"""

VULNS_PROMPT = """Basandoti sul codice fornito e sulle regole CTF generali, identifica tutte le potenziali vulnerabilità. Per ogni vulnerabilità, rispondi in **italiano**:
**Sintesi Vulnerabilità:** [Nome_Conciso_della_Vulnerabilità, es. SQL_Injection, Buffer_Overflow, XSS]
1. Descrivi dettagliatamente la vulnerabilità.
2. Spiega come può essere innescata (triggerata), considerando le specifiche del CTF (es. input, interazione di rete).
3. Discuti il suo potenziale impatto (es. esecuzione arbitraria di codice, denial of service, divulgazione di informazioni), e come questo si traduce in un vantaggio nel CTF (es. cattura flag, impatto sul punteggio SLA).
4. Suggerisci strategie di mitigazione di alto livello.
"""

MERGE_PROMPT_TEMPLATE = """
Ho ricevuto diverse analisi di vulnerabilità per un codebase da vari modelli AI.
Il tuo compito è rivedere tutte le analisi fornite, consolidare i risultati chiave e quindi generare un codice exploit completo e robusto che affronti le vulnerabilità identificate da tutti i modelli, tenendo conto delle regole e del contesto del CTF.

Ecco le analisi di vulnerabilità consolidate:
{all_vulnerability_analyses}

Basandoti su queste analisi, e considerando le regole CTF fornite (formato flag, metodi di invio, struttura di rete, ecc.), fornisci, in **italiano**:
1. Un breve riassunto delle vulnerabilità più critiche identificate e il loro potenziale impatto CTF.
2. Il codice exploit consolidato e robusto. Assicurati che il codice sia pronto per la produzione, ben commentato e includa tutte le istruzioni necessarie per la configurazione o l'utilizzo, adattandosi all'ambiente CTF (es. indirizzi IP, formato flag). Il codice dovrebbe includere la logica per estrarre la flag e inviarla al servizio di invio flag se l'exploit lo consente.
   Il codice exploit deve essere racchiuso tra triple backtick (```python ... ```). Non includere spiegazioni o testo al di fuori del blocco di codice.
   
**IMPORTANTE:** Basati sulla "Sintesi Vulnerabilità" fornita nelle analisi per un nome conciso da includere nel nome del file dell'exploit. Se più sintesi sono presenti, usa quella più rilevante o la prima.
"""

# --- Chat Responses (for context building) ---
RESPONSES = [
    "Compreso. Ora analizzerò `{}` per le vulnerabilità, considerando le regole CTF.",
    "Ricevuto. Sto elaborando `{}` per trovare difetti di sicurezza e generare exploit CTF-ready.",
    "File `{}` ricevuto. Sto scansionando per potenziali exploit nel contesto del CTF.",
    "Capito. Sto esaminando `{}` per eventuali debolezze sfruttabili nel CTF.",
    "Bene. Analizzo `{}` per vulnerabilità rilevanti per le CTF, tenendo conto delle regole di gioco."
]

# --- Exploit Template Path ---
EXPLOIT_TEMPLATE_PATH = "templates/exp_template.py"

# --- File Collection Configuration ---
DEFAULT_MAX_FILE_SIZE_KB = 30 # Default max file size for collection in KB
EXCLUDE_DIRS = ["/.git/", "/.vscode/", "/__pycache__/"] # Directories to exclude from collection

# --- Output File Configuration ---
EXPLOIT_FILENAME_PREFIX = "exploit_"
EXPLOIT_FILENAME_SUFFIX = ".py"
EXPLOIT_DIR = "exploits"

# --- Logging Configuration ---
LOG_FILE = "errors.log"

# --- UI Colors ---
COLORS = {
    "DEBUG": "\033[94m",    # Blue
    "INFO": "\033[92m",     # Green
    "WARNING": "\033[93m",  # Yellow
    "ERROR": "\033[91m",    # Red
    "CRITICAL": "\033[95m", # Magenta
}
COLOR_RESET = "\033[0m"