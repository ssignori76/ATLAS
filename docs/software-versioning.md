# 🔧 ATLAS Software Versioning Guide

## ✅ Risposta alla tua domanda

**Sì, è possibile rendere opzionale la versione del software!** Il sistema ATLAS supporta già completamente questa funzionalità. Quando non specifichi una versione, il sistema utilizza automaticamente l'ultima versione disponibile.

## 🚀 Come funziona

### 📋 Configurazione Base (tua configurazione attuale)

```yaml
# vm-config.yaml
vms:
  - hostname: "web-server-01"
    cpu: 4
    memory: 8192
    disk: 100
    os: "ubuntu22"
    software:
      - nginx              # ✅ Automaticamente usa l'ultima versione
      - docker             # ✅ Automaticamente usa l'ultima versione
      - monitoring-agent   # ✅ Automaticamente usa l'ultima versione
      
  - hostname: "db-server-01"  
    cpu: 8
    memory: 16384
    disk: 500
    os: "ubuntu22"
    software:
      - postgresql         # ✅ Automaticamente usa l'ultima versione
      - backup-tools       # ✅ Automaticamente usa l'ultima versione
```

**Risultato**: Quando ATLAS provisiona queste VM, risolverà automaticamente:
- `nginx` → `nginx v1.24.0` (ultima versione APT)
- `docker` → `docker v24.0.7` (ultima versione Docker Hub)
- `postgresql` → `postgresql v15.4` (ultima versione APT)

## 🎯 Configurazioni Avanzate

### 1. **Versioni Miste** (alcune specifiche, altre automatic)

```yaml
vms:
  - hostname: "web-server-mixed"
    software:
      - nginx                           # Latest automatico
      - name: postgresql
        version: "14.9"                 # Versione specifica per stabilità
      - name: docker
        version: "latest"               # Latest esplicito
      - name: nodejs
        version: "~18.0"                # Range di versioni (18.x)
      - git                             # Latest automatico
```

### 2. **Ambiente di Produzione** (controllo preciso)

```yaml
vms:
  - hostname: "prod-server"
    software:
      - name: nginx
        version: "1.22.1"              # Versione testata
      - name: postgresql  
        version: "14.9"                 # LTS per stabilità
      - fail2ban                        # Latest per sicurezza
      - name: certbot
        version: "lts"                  # Versione LTS
```

### 3. **Ambiente di Sviluppo** (flessibilità massima)

```yaml
vms:
  - hostname: "dev-server"
    software:
      - name: python
        version: "3.11.5"              # Versione team standard
      - name: nodejs
        version: "18.17.0"             # Consistency sviluppo
      - docker                          # Latest per nuove features
      - git                             # Latest
      - vim                             # Latest
```

## 📚 Formati Supportati

### Formato Semplice (latest automatico)
```yaml
software:
  - nginx
  - docker
  - git
```

### Formato Esteso (controllo completo)
```yaml
software:
  - name: nginx
    version: "1.22.1"          # Versione specifica
    source: apt                # Fonte del package
    config:                    # Configurazione personalizzata
      worker_processes: auto
  
  - name: docker
    version: "^24.0"           # Range compatibile (24.x)
    
  - name: nodejs
    version: "~18.0"           # Range specifico (18.x)
    source: snap
```

## 🔍 Tipi di Versioni Supportate

| Tipo | Esempio | Descrizione |
|------|---------|-------------|
| **Omessa** | `nginx` | Usa automaticamente l'ultima versione |
| **Latest esplicito** | `version: "latest"` | Esplicitamente l'ultima |
| **Versione esatta** | `version: "1.22.1"` | Versione specifica |
| **Range compatibile** | `version: "^24.0"` | Compatibile con 24.x |
| **Range specifico** | `version: "~18.0"` | Famiglia 18.x |
| **Versioni speciali** | `version: "lts"` | LTS, stable, etc. |

## ⚙️ Come il Sistema Risolve le Versioni

1. **Analisi**: Il sistema analizza ogni package nella configurazione
2. **Auto-detection**: Rileva automaticamente la fonte (apt, docker, snap, etc.)
3. **Risoluzione**: Interroga i repository per le versioni disponibili
4. **Selezione**: Sceglie la versione appropriata:
   - Se non specificata → ultima disponibile
   - Se specificata → quella richiesta (con validazione)
5. **Cache**: Memorizza i risultati per performance
6. **Installazione**: Procede con l'installazione

## 🛠️ Utilizzo Pratico

### Comando CLI base
```bash
atlas provision vm-config.yaml
```

### Con risoluzione versioni (consigliato)
```bash
atlas provision vm-config.yaml --resolve-versions
```

### Preview senza installazione
```bash
atlas provision vm-config.yaml --dry-run
```

### Validazione configurazione
```bash
atlas validate vm-config.yaml
```

## 📋 Template di Esempio

### Server Web Basic
```yaml
vms:
  - hostname: "web-basic"
    cpu: 2
    memory: 2048
    disk: 50
    os: "ubuntu-22.04"
    software:
      - nginx        # Latest web server
      - certbot      # Latest SSL certificates
      - fail2ban     # Latest security
```

### Database Server
```yaml
vms:
  - hostname: "db-server"
    cpu: 4
    memory: 8192
    disk: 200
    os: "ubuntu-22.04"
    software:
      - name: postgresql
        version: "14.9"      # LTS per produzione
      - name: redis
        version: "stable"    # Cache stabile
      - backup-tools         # Latest backup utilities
```

### Development Environment
```yaml
vms:
  - hostname: "dev-env"
    cpu: 4
    memory: 4096
    disk: 100
    os: "ubuntu-22.04"
    software:
      - name: python
        version: "3.11"      # Python team standard
      - name: nodejs  
        version: "~18.0"     # Node.js LTS
      - docker               # Latest containerization
      - git                  # Latest version control
      - vim                  # Latest editor
```

## 🎯 Vantaggi

✅ **Semplicità**: Configurazioni pulite e leggibili  
✅ **Flessibilità**: Mix di versioni automatiche e specifiche  
✅ **Compatibilità**: Funziona con configurazioni esistenti  
✅ **Sicurezza**: Sempre aggiornato per package di sicurezza  
✅ **Controllo**: Versioni precise quando necessario  
✅ **Performance**: Cache e risoluzione intelligente  

## 🚀 Conclusione

Il sistema ATLAS **già supporta completamente** il versioning flessibile che hai richiesto:

- ✅ **Versioni opzionali**: Ometti la versione per ottenere l'ultima
- ✅ **Risoluzione automatica**: Il sistema trova la versione migliore
- ✅ **Retrocompatibilità**: Le tue configurazioni attuali funzionano già
- ✅ **Configurazioni miste**: Combina approcci diversi nella stessa VM
- ✅ **Documentazione completa**: Guide ed esempi pronti all'uso

**Non sono necessarie modifiche** alla tua configurazione attuale - funziona già come desideri!
