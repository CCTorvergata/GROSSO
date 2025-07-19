# G.R.O.S.S.O.
**Gemini Recon & OpenAI Secure System Orchestration**

<img src="https://github.com/CCTorvergata/GROSSO/blob/main/logo/grosso_logo.png" alt="GROSSO Auto Prompter" width="300"/>

Questo progetto automatizza il prompting di Large Language Models (LLM) per tutti i file in una directory di sfida, consentendo un'analisi rapida delle vulnerabilità e la generazione di exploit in CTF di tipo Attack-Defense. Supporta l'integrazione con i modelli Google Gemini e OpenAI GPT.

---

## 🔧 Utilizzo

1.  **Clona il repository:**
    ```bash
    git clone [https://github.com/CCTorvergata/GROSSO.git](https://github.com/CCTorvergata/GROSSO.git)
    cd GROSSO
    ```

2.  **Crea e attiva un ambiente virtuale (raccomandato):**
    ```bash
    python3 -m venv venv
    source venv/bin/activate  # Linux/macOS
    # o per Windows:
    # venv\Scripts\activate
    ```

3.  **Installa le dipendenze:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configura le tue API Key:**
    Crea un file `.env` nella directory principale del progetto. Questo file **non deve essere mai committato** nel controllo versione, in quanto conterrà le tue chiavi API private.

    Le API Key saranno lette automaticamente dal file `.env`. Puoi fornire una chiave principale e/o chiavi numerate per avere più opzioni di fallback.

    * **Per Google Gemini:**
        1.  Vai su [Google AI Studio](https://aistudio.google.com/app/apikey) e accedi con il tuo account Google.
        2.  Crea una nuova API key (o riutilizzane una esistente).
        3.  Aggiungi la chiave al tuo file `.env` nel seguente formato:
            ```
            GOOGLE_API_KEY=il_tuo_gemini_api_key
            ```
            Puoi anche aggiungere chiavi multiple per ridondanza, come:
            ```
            GOOGLE_API_KEY_1=chiave_1
            GOOGLE_API_KEY_2=chiave_2
            ```

    * **Per OpenAI (GPT):**
        1.  Vai su [OpenAI Platform](https://platform.openai.com/api-keys) e accedi al tuo account.
        2.  Crea una nuova "Secret key". Assicurati di copiare la chiave immediatamente perché non sarà mostrata di nuovo.
        3.  Aggiungi la chiave al tuo file `.env` nel seguente formato:
            ```
            OPENAI_API_KEY=la_tua_openai_api_key
            ```
            Puoi anche aggiungere chiavi multiple per ridondanza, come:
            ```
            OPENAI_API_KEY_1=chiave_1
            OPENAI_API_KEY_2=chiave_2
            ```
    
    Un esempio di file `.env` potrebbe essere:
    ```
    GOOGLE_API_KEY=AIzaSy...
    OPENAI_API_KEY=sk-...
    GOOGLE_API_KEY_1=AIzaSy...
    OPENAI_API_KEY_1=sk-...
    ```

5.  **Esegui lo script:**
    ```bash
    python3 main.py -p PATH [-ms MAXSIZE] [-t TIMEOUT]
    ```

### Disabilitare uno dei modelli AI

Per disabilitare temporaneamente o permanentemente l'utilizzo di Gemini o OpenAI, puoi modificare il file `config.py`.

Cerca la sezione `MODELS` e commenta o rimuovi la riga relativa al provider che desideri disabilitare:

```python
# config.py

# --- API Configuration ---
MODELS = {
    "gemini": ["models/gemini-2.5-pro", "models/gemini-2.5-flash"],
    # "openai": ["gpt-4o", "gpt-4o-mini"], # Decommenta o rimuovi questa riga per disabilitare OpenAI
}

# Oppure per disabilitare Gemini:
# MODELS = {
#     # "gemini": ["models/gemini-2.5-pro", "models/gemini-2.5-flash"], # Decommenta o rimuovi questa riga per disabilitare Gemini
#     "openai": ["gpt-4o", "gpt-4o-mini"],
# }

# Se vuoi disabilitare entrambe, puoi impostare MODELS a un dizionario vuoto:
# MODELS = {}

# ... altre configurazioni
```

### Parametri

* **-p PATH** o **--path PATH**: Il percorso della directory contenente i file della sfida o il percorso di un singolo file (obbligatorio).
* **-ms MAXSIZE** o **--max-size MAXSIZE**: Dimensione massima (in kilobyte) consentita per un singolo file da includere nel prompt (opzionale, predefinito: 30 KB).
* **-t TIMEOUT** o **--timeout TIMEOUT**: Tempo massimo (in secondi) di attesa per la prima risposta da un modello. Se il timeout scade, lo script passa a un altro modello/chiave (opzionale, predefinito: 300 secondi).

### Scorciatoie utili per la chat interattiva:
- **Esc + Enter**: Inserisci una nuova riga nel prompt
- **Ctrl + X**: Copia il codice dell'ultimo exploit generato