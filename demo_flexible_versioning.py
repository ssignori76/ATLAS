#!/usr/bin/env python3
"""
Demo script to show ATLAS flexible software versioning capabilities.

This demonstrates how the system handles optional software versions,
falling back to 'latest' when no version is specified.
"""

import yaml
from typing import Dict, Any, List, Optional
from dataclasses import dataclass


@dataclass
class SoftwarePackage:
    """Simplified software package model."""
    name: str
    version: Optional[str] = None
    source: Optional[str] = None
    config: Optional[Dict[str, Any]] = None


def parse_software_config(software_list: List[Any]) -> List[SoftwarePackage]:
    """Parse software configuration supporting both string and object formats."""
    packages = []
    
    for item in software_list:
        if isinstance(item, str):
            # Simple string format: "nginx" -> SoftwarePackage(name="nginx", version=None)
            packages.append(SoftwarePackage(name=item))
        elif isinstance(item, dict):
            # Object format with optional version
            packages.append(SoftwarePackage(
                name=item.get('name'),
                version=item.get('version'),
                source=item.get('source'),
                config=item.get('config')
            ))
    
    return packages


def resolve_version(package: SoftwarePackage) -> str:
    """Mock version resolution - in real system this would query repositories."""
    
    # Mock latest versions database
    latest_versions = {
        'nginx': '1.24.0',
        'docker': '24.0.7', 
        'postgresql': '15.4',
        'nodejs': '20.8.0',
        'python': '3.11.5',
        'git': '2.42.0',
        'vim': '9.0',
        'redis': '7.2.3',
        'certbot': '2.7.4',
        'fail2ban': '1.0.2',
        'monitoring-agent': '1.5.0',
        'backup-tools': '2.1.0'
    }
    
    if package.version:
        # Version specified - return as-is (in real system would validate)
        return package.version
    else:
        # No version specified - return latest
        return latest_versions.get(package.name, 'latest')


def demo_configuration_parsing():
    """Demonstrate parsing of your original configuration."""
    
    print("🚀 ATLAS Software Versioning Demo")
    print("=" * 60)
    print()
    
    # Your original configuration 
    config_yaml = """
vms:
  - hostname: "web-server-01"
    cpu: 4
    memory: 8192
    disk: 100
    os: "ubuntu22"
    software:
      - nginx
      - docker
      - monitoring-agent
      
  - hostname: "db-server-01"  
    cpu: 8
    memory: 16384
    disk: 500
    os: "ubuntu22"
    software:
      - postgresql
      - backup-tools
"""
    
    print("📋 Configuration originale:")
    print(config_yaml)
    
    # Parse the configuration
    config = yaml.safe_load(config_yaml)
    
    print("🔍 Analisi delle VM e risoluzione versioni software:")
    print("-" * 60)
    
    for i, vm in enumerate(config['vms'], 1):
        print(f"\n🖥️  VM {i}: {vm['hostname']}")
        print(f"   CPU: {vm['cpu']} cores, RAM: {vm['memory']} MB, Disk: {vm['disk']} GB")
        print(f"   OS: {vm['os']}")
        print("   Software:")
        
        # Parse software packages
        packages = parse_software_config(vm['software'])
        
        for pkg in packages:
            resolved_version = resolve_version(pkg)
            status = "✅ Latest" if pkg.version is None else f"📌 Specificata: {pkg.version}"
            print(f"     • {pkg.name} → v{resolved_version} ({status})")


def demo_enhanced_configurations():
    """Show enhanced configuration examples with optional versioning."""
    
    print("\n" + "=" * 60)
    print("📚 Esempi di configurazioni avanzate")
    print("=" * 60)
    
    examples = [
        {
            "name": "Web Server con versioni miste",
            "config": {
                "hostname": "web-mixed-01",
                "software": [
                    "nginx",  # Nessuna versione = latest
                    {"name": "postgresql", "version": "14.9"},  # Versione specifica
                    {"name": "docker", "version": "latest"},    # Latest esplicito
                    {"name": "nodejs", "version": "~18.0"},     # Range versioni
                    "git"  # Latest implicito
                ]
            }
        },
        {
            "name": "Server di produzione stabile",
            "config": {
                "hostname": "prod-stable-01", 
                "software": [
                    {"name": "nginx", "version": "1.22.1"},     # Versione testata
                    {"name": "postgresql", "version": "14.9"},  # LTS database
                    "fail2ban",  # Latest per sicurezza
                    {"name": "certbot", "version": "lts"}       # Versione LTS
                ]
            }
        },
        {
            "name": "Ambiente di sviluppo",
            "config": {
                "hostname": "dev-env-01",
                "software": [
                    {"name": "python", "version": "3.11.5"},    # Versione team
                    {"name": "nodejs", "version": "18.17.0"},   # Consistency  
                    "docker",  # Latest per nuove features
                    "git",     # Latest
                    "vim"      # Latest
                ]
            }
        }
    ]
    
    for example in examples:
        print(f"\n📋 {example['name']}:")
        print(f"   Hostname: {example['config']['hostname']}")
        print("   Software:")
        
        packages = parse_software_config(example['config']['software'])
        
        for pkg in packages:
            resolved_version = resolve_version(pkg)
            
            if pkg.version is None:
                status_icon = "🔄"
                status_text = "Auto-latest"
            elif pkg.version in ['latest', 'lts', 'stable']:
                status_icon = "⚙️"
                status_text = f"Speciale: {pkg.version}"
            else:
                status_icon = "📌"
                status_text = f"Fissa: {pkg.version}"
            
            print(f"     {status_icon} {pkg.name} → v{resolved_version} ({status_text})")


def show_benefits():
    """Show the benefits of flexible versioning."""
    
    print("\n" + "=" * 60)
    print("✨ Vantaggi del Sistema di Versioning Flessibile")
    print("=" * 60)
    
    benefits = [
        "🔄 **Semplicità**: Ometti la versione per ottenere automaticamente l'ultima",
        "📌 **Controllo**: Specifica versioni esatte quando necessario",
        "🎯 **Flessibilità**: Usa range di versioni (~18.0, ^24.0) per compatibilità",
        "🛡️ **Stabilità**: Versioni LTS/stable per ambienti di produzione",
        "⚙️ **Configurazione mista**: Combina approcci diversi nella stessa VM",
        "🔍 **Risoluzione automatica**: Il sistema risolve le versioni al momento del provisioning",
        "📚 **Documentazione chiara**: Configurazioni leggibili e comprensibili"
    ]
    
    for benefit in benefits:
        print(f"  {benefit}")
    
    print("\n🎯 **Esempio pratico**: Se specifichi solo 'nginx', il sistema:")
    print("  1. Rileva automaticamente che è un package APT")
    print("  2. Interroga il repository per l'ultima versione disponibile")
    print("  3. Installa nginx con la versione più recente")
    print("  4. Mantiene un log della versione installata per riferimenti futuri")


if __name__ == "__main__":
    demo_configuration_parsing()
    demo_enhanced_configurations()
    show_benefits()
    
    print("\n🎉 Demo completata!")
    print("\n💡 Il sistema ATLAS supporta già completamente il versioning flessibile!")
    print("   - Basta omettere il campo 'version' per ottenere l'ultima versione")
    print("   - Il sistema è retrocompatibile con configurazioni esistenti")
    print("   - Nessuna modifica necessaria al codice esistente")
