#!/usr/bin/env python3
"""
ATLAS CLI with enhanced software version management.

This script demonstrates the integration of the version resolver
with the CLI for user-friendly software management.
"""

import asyncio
import click
import yaml
from typing import List, Dict, Any

from atlas.core.models import VMSpec, SoftwarePackage
from atlas.core.version_resolver import VersionResolver, PackageSource


@click.group()
def cli():
    """ATLAS - AI-Assisted Proxmox VM Provisioning"""
    pass


@cli.command()
@click.argument('config_file', type=click.Path(exists=True))
@click.option('--resolve-versions/--no-resolve-versions', default=True,
              help='Resolve and display actual software versions')
@click.option('--dry-run', is_flag=True, help='Show what would be installed without provisioning')
def provision(config_file: str, resolve_versions: bool, dry_run: bool):
    """Provision VM from configuration file."""
    
    with open(config_file, 'r') as f:
        config_data = yaml.safe_load(f)
    
    # Parse VM specification
    vm_spec = VMSpec(**config_data)
    
    if resolve_versions and vm_spec.software:
        click.echo("🔍 Resolving software versions...")
        resolved_software = asyncio.run(resolve_software_versions(vm_spec.software))
        
        # Display resolved versions
        click.echo("\n📦 Software Packages:")
        for pkg in resolved_software:
            version_text = f"v{pkg.resolved_version}" if pkg.resolved_version != "latest" else "latest"
            source_text = f"[{pkg.source}]" if pkg.source else ""
            click.echo(f"  • {pkg.package_name} {version_text} {source_text}")
        
        if dry_run:
            click.echo("\n✅ Dry run complete. No VM was provisioned.")
            return
    
    if not dry_run:
        click.echo(f"\n🚀 Provisioning VM: {vm_spec.name}")
        # Here would be the actual provisioning logic
        click.echo("✅ VM provisioned successfully!")


@cli.command()
@click.argument('package_name')
@click.option('--version', help='Specific version to resolve')
@click.option('--source', type=click.Choice(['apt', 'docker', 'snap', 'npm', 'pip']),
              help='Package source')
def resolve_version(package_name: str, version: str, source: str):
    """Resolve a specific software version."""
    
    async def _resolve():
        async with VersionResolver() as resolver:
            resolved = await resolver.resolve_version(
                package_name, 
                version, 
                PackageSource(source) if source else None
            )
            return resolved
    
    resolved = asyncio.run(_resolve())
    
    click.echo(f"📦 Package: {resolved.package_name}")
    click.echo(f"🎯 Requested: {resolved.requested_version or 'latest'}")  
    click.echo(f"✅ Resolved: {resolved.resolved_version}")
    click.echo(f"📡 Source: {resolved.source}")
    
    if resolved.download_url:
        click.echo(f"🔗 URL: {resolved.download_url}")


@cli.command()
@click.argument('config_file', type=click.Path(exists=True))
def validate(config_file: str):
    """Validate VM configuration file."""
    
    try:
        with open(config_file, 'r') as f:
            config_data = yaml.safe_load(f)
        
        # Validate configuration
        vm_spec = VMSpec(**config_data)
        
        click.echo("✅ Configuration is valid!")
        click.echo(f"VM Name: {vm_spec.name}")
        click.echo(f"OS: {vm_spec.os_type}")
        click.echo(f"CPU: {vm_spec.cores} cores")
        click.echo(f"Memory: {vm_spec.memory} MB")
        
        if vm_spec.software:
            click.echo(f"Software Packages: {len(vm_spec.software)}")
            for pkg in vm_spec.software:
                if isinstance(pkg, str):
                    click.echo(f"  • {pkg} (latest)")
                else:
                    version_text = pkg.version or "latest"
                    click.echo(f"  • {pkg.name} ({version_text})")
        
    except Exception as e:
        click.echo(f"❌ Configuration error: {e}", err=True)
        raise click.Abort()


@cli.command()
def list_examples():
    """List available configuration examples."""
    
    examples = {
        "basic": "Basic web server with latest software versions",
        "development": "Development environment with specific tool versions", 
        "production": "Production-ready with stable/LTS versions",
        "microservices": "Containerized microservices stack",
        "database": "Database server with PostgreSQL",
        "minimal": "Minimal server configuration"
    }
    
    click.echo("📚 Available Configuration Examples:")
    for name, description in examples.items():
        click.echo(f"  • {name}: {description}")
    
    click.echo("\nℹ️  Use 'atlas generate-example <name>' to create a template")


@cli.command()
@click.argument('example_name')
@click.option('--output', '-o', default='vm-config.yaml', help='Output file name')
def generate_example(example_name: str, output: str):
    """Generate example configuration file."""
    
    examples = {
        "basic": {
            "name": "web-server-basic",
            "os_type": "ubuntu-22.04",
            "memory": 2048,
            "cores": 2,
            "software": ["nginx", "docker", "git"]
        },
        "development": {
            "name": "dev-environment", 
            "os_type": "ubuntu-22.04",
            "memory": 4096,
            "cores": 4,
            "software": [
                {"name": "python", "version": "3.11"},
                {"name": "nodejs", "version": "~18.0"},
                {"name": "docker", "version": "latest"},
                "git", "vim", "htop"
            ]
        },
        "production": {
            "name": "prod-web-server",
            "os_type": "ubuntu-22.04", 
            "memory": 8192,
            "cores": 4,
            "software": [
                {"name": "nginx", "version": "1.22.1"},
                {"name": "certbot", "version": "lts"},
                "fail2ban", "ufw"
            ]
        }
    }
    
    if example_name not in examples:
        click.echo(f"❌ Unknown example: {example_name}", err=True)
        click.echo("Use 'atlas list-examples' to see available examples")
        raise click.Abort()
    
    config = examples[example_name]
    
    with open(output, 'w') as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False)
    
    click.echo(f"✅ Generated example configuration: {output}")
    click.echo(f"🔍 Edit the file and run: atlas provision {output}")


async def resolve_software_versions(software_list: List[SoftwarePackage]) -> List:
    """Resolve versions for a list of software packages."""
    
    async with VersionResolver() as resolver:
        resolved_packages = []
        
        for pkg in software_list:
            if isinstance(pkg, str):
                # Simple string format - convert to SoftwarePackage
                pkg = SoftwarePackage(name=pkg)
            
            try:
                resolved = await resolver.resolve_version(
                    pkg.name,
                    pkg.version,
                    PackageSource(pkg.source) if pkg.source else None
                )
                resolved_packages.append(resolved)
            except Exception as e:
                click.echo(f"⚠️  Warning: Could not resolve {pkg.name}: {e}")
                # Create a fallback resolved version
                from atlas.core.version_resolver import ResolvedVersion
                resolved_packages.append(ResolvedVersion(
                    package_name=pkg.name,
                    requested_version=pkg.version,
                    resolved_version=pkg.version or "latest", 
                    source=PackageSource(pkg.source) if pkg.source else PackageSource.APT
                ))
        
        return resolved_packages


if __name__ == '__main__':
    cli()
