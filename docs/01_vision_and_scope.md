# 💡 1. Visione e Perimetro del Progetto

**Documento:** Vision & Scope  
**Progetto:** Atlas - Collaboratore AI per Infrastrutture  
**Versione:** 1.0  
**Data:** 29 Giugno 2025

---

## 1. Visione

Creare un **assistente basato su Intelligenza Artificiale ("Atlas")** che agisca come un collaboratore esperto per i team di Technology & Architecture. La visione è quella di trasformare requisiti di alto livello in ambienti infrastrutturali funzionanti, testati e documentati, automatizzando le fasi di design e testing per accelerare il delivery e aumentare l'affidabilità.

---

## 2. Problema

Attualmente, il processo di creazione e configurazione di nuovi ambienti è caratterizzato da diverse criticità:

* **Processi Manuali Lenti:** La scrittura di playbook Ansible e la configurazione manuale di VM sono attività che richiedono tempo e sono soggette a colli di bottiglia.
* **Rischio di Errori e Inconsistenze:** L'intervento manuale può portare a errori di configurazione e a implementazioni non standard tra diversi progetti.
* **Ciclo di Test Ripetitivo:** Il provisioning di VM di test, l'esecuzione dei playbook e la validazione sono operazioni manuali e ripetitive che sottraggono tempo a compiti di maggior valore.

---

## 3. Obiettivi e Metriche di Successo (KPI)

Gli obiettivi misurabili che questo progetto si prefigge di raggiungere con l'MVP sono:

* **Velocità:** Ridurre del **70%** il tempo necessario per creare e testare un playbook Ansible per una configurazione standard.
* **Qualità:** Eliminare gli errori di sintassi e di configurazione comuni nei playbook generati automaticamente.
* **Standardizzazione:** Garantire che il **100%** delle configurazioni generate tramite l'assistente segua le best practice aziendali definite.

---

## 4. Perimetro (Scope)

### Incluso nel Perimetro dell'MVP (In-Scope)

L'MVP si concentrerà esclusivamente sull'**Epic 1: Provisioning Ex Novo (Greenfield)**. Le funzionalità specifiche includono:

1.  **Input:** L'assistente accetterà un file di configurazione `YAML` che descrive un ambiente con una o più VM.
2.  **Provider:** Il solo provider di virtualizzazione supportato sarà **`virsh`** (KVM/QEMU).
3.  **Tool di Provisioning:** Il solo tool di configurazione supportato sarà **Ansible**.
4.  **Output:** L'assistente genererà:
    * Le VM di test necessarie.
    * I playbook Ansible corrispondenti alle specifiche.
    * Un report finale sull'esito dell'operazione.

### Escluso dal Perimetro dell'MVP (Out-of-Scope)

Le seguenti funzionalità sono considerate per versioni future ma non faranno parte dello sviluppo iniziale:

* **Epic 2:** Supporto all'aggiornamento o analisi di ambienti esistenti (Brownfield).
* **Supporto Multi-Provider:** Integrazione con provider cloud come AWS, Azure o Google Cloud.
* **Supporto Multi-Tool:** Integrazione con altri tool di IaC come Terraform o Pulumi.
* **Interfacce Grafiche (GUI):** L'interazione avverrà unicamente tramite interfaccia a riga di comando (CLI).

---

## 5. Stakeholder

* **Utenti Finali:** DevOps Engineers, System Architects, Sviluppatori.
* **Beneficiari:** Management (aumento efficienza), Team di Sicurezza (garanzia degli standard).
