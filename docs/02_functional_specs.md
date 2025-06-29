# 🎯 2. Specifiche Funzionali

**Documento:** Specifiche Funzionali  
**Progetto:** Atlas - Collaboratore AI per Infrastrutture  
**Versione:** 1.0  
**Data:** 29 Giugno 2025

---

## Introduzione

Questo documento descrive le funzionalità dell'assistente AI "Atlas" attraverso la definizione di Epiche e User Story. L'approccio di sviluppo si concentrerà sull'implementazione dell'Epic 1 per il Minimum Viable Product (MVP).

---

## 🌳 Epic 1: Provisioning di un Ambiente Ex Novo (Greenfield)

**Stato:** scoped per l'MVP

**Obiettivo:** Permettere a un utente di descrivere un ambiente desiderato in un file di configurazione e ottenere automaticamente le VM, i playbook Ansible e la documentazione necessari per crearlo.

### User Stories

* **1.1 - Definizione Input:** Come utente, voglio poter descrivere le specifiche del mio ambiente (VM, OS, pacchetti software, configurazioni) utilizzando un formato strutturato `YAML` per fornirlo all'assistente AI.

* **1.2 - Interpretazione AI:** Come assistente AI, devo essere in grado di analizzare il file di specifiche `YAML`, validarne la correttezza e pianificare i passi necessari (es. quante VM creare, quali componenti software installare).

* **1.3 - Provisioning VM:** Come assistente AI, devo usare i comandi `virsh` per creare una o più VM di test in base al piano, configurando le risorse (CPU, RAM, disco) e la rete come richiesto.

* **1.4 - Generazione Playbook Ansible:** Come assistente AI, devo interpretare i dettagli di configurazione in linguaggio naturale per ogni componente software e generare i task di un playbook Ansible idempotente che esegua tali configurazioni.

* **1.5 - Generazione Documentazione:** Come assistente AI, devo produrre una guida in formato Markdown che descriva l'architettura creata, i playbook generati e il loro scopo.

* **1.6 - Esecuzione e Report:** Come utente, voglio che l'assistente AI esegua i playbook generati sulle VM di test, catturi l'output e mi fornisca un report finale che attesti il successo o il fallimento dell'operazione, con i relativi log.

---

## 🏚️ Epic 2: Aggiornamento di un Ambiente Esistente (Brownfield)

**Stato:** fuori scope per l'MVP

**Obiettivo:** Permettere a un utente di indicare un ambiente esistente per analizzarlo, replicarlo o aggiornarlo in modo controllato.

### User Stories

* **2.1 - Connessione e Discovery:** Come assistente AI, devo potermi collegare in modo sicuro a macchine esistenti per raccogliere informazioni su sistema operativo, pacchetti installati e configurazioni.

* **2.2 - Assessment ("Diffing"):** Come assistente AI, devo essere in grado di identificare le differenze tra lo stato attuale di un sistema e lo stato desiderato.

* **2.3 - Generazione Piano di Modifica:** Come assistente AI, devo generare un piano di modifica dettagliato che elenchi le azioni necessarie per l'aggiornamento.

* **2.4 - Replicazione Ambiente di Test:** Come assistente AI, devo usare `virsh` per creare un ambiente di test che sia una replica fedele di quello analizzato.

* **2.5 - Generazione Playbook di Aggiornamento:** Come assistente AI, devo generare playbook Ansible specifici per applicare solo le modifiche identificate nel piano.

* **2.6 - Esecuzione Controllata:** Come utente, voglio che l'assistente esegua i playbook di aggiornamento sull'ambiente di test replicato e mi fornisca un report dettagliato.
