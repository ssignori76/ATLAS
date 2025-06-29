# 🤖 Progetto Atlas: Collaboratore AI per il T&A

Questo repository contiene il codice sorgente per "Atlas", un assistente basato su IA progettato per automatizzare il design, il provisioning e il testing di infrastrutture IT. L'obiettivo è trasformare requisiti di alto livello in ambienti funzionanti e documentati, riducendo il lavoro manuale e gli errori.

**Stato del Progetto:** 🚧 In Sviluppo (MVP) 🚧

---

## ✨ Concetto e Visione

La visione di Atlas è quella di agire come un "collega" esperto per i team di Technology & Architecture. L'utente fornisce un file di configurazione con le specifiche desiderate e Atlas si occupa del resto.

Lo sviluppo è suddiviso in due epiche principali:

1.  🌳 **Epic 1: Provisioning Ex Novo (Greenfield)** - Creazione di nuovi ambienti da zero basandosi su specifiche chiare.
2.  🏚️ **Epic 2: Aggiornamento Esistente (Brownfield)** - Analisi e modifica di ambienti già esistenti.

> Per una descrizione dettagliata di ogni Epica e delle relative User Story, consulta il documento:
> **[`docs/02_functional_specs.md`](./docs/02_functional_specs.md)**

---

## 🚀 Getting Started

Per avviare il progetto in locale, segui questi passi.

### Prerequisiti

* [Git](https://git-scm.com/)
* [Python](https://www.python.org/downloads/) 3.9+
* Un hypervisor che supporti `virsh` (es. KVM/QEMU su Linux)

### Installazione

1.  **Clona il repository:**
    ```bash
    git clone <URL_DEL_TUO_REPOSITORY_GIT>
    cd atlas-ai-project
    ```

2.  **Crea e attiva un ambiente virtuale (consigliato):**
    ```bash
    # Su Linux/macOS
    python3 -m venv venv
    source venv/bin/activate

    # Su Windows
    python -m venv venv
    .\venv\Scripts\activate
    ```

3.  **Installa le dipendenze:**
    ```bash
    pip install -r requirements.txt
    ```

---

## 🛠️ Utilizzo

1.  **Copia il file di configurazione di esempio:**
    ```bash
    cp config.example.yaml my_first_project.yaml
    ```

2.  **Modifica `my_first_project.yaml`** per definire l'ambiente che desideri creare.

3.  **Lancia l'assistente AI:**
    ```bash
    python atlas/main.py --config my_first_project.yaml
    ```

L'assistente leggerà il file di configurazione, genererà il playbook Ansible e avvierà il processo di provisioning nella directory `workspace/`.

---

## 📚 Struttura del Progetto

* `atlas/`: Codice sorgente principale dell'applicazione.
* `docs/`: Documentazione funzionale e di architettura.
* `iac_templates/`: Template Jinja2 per la generazione di codice (es. Playbook Ansible).
* `tests/`: Test automatici.
* `workspace/`: File temporanei e output generati dall'AI.
````
