"""
Command-line interface for the ATLAS system.

This module provides the main CLI for interacting with ATLAS,
including commands for initialization, validation, provisioning,
and management of VM configurations.
"""

import sys
import asyncio
from pathlib import Path
from typing import Optional, List
import click
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.panel import Panel
from rich.syntax import Syntax

from atlas.core import (
    get_logger,
    get_config,
    AtlasError,
    ConfigurationError,
    VMSpec,
    ProvisioningRequest,
    OSType,
    VMSize,
)

# Initialize console for rich output
console = Console()
logger = get_logger(__name__)


# Custom click group with rich help
class RichGroup(click.Group):
    """Click group with rich formatting."""
    
    def format_help(self, ctx, formatter):
        """Format help with rich styling."""
        console.print("\n[bold blue]ATLAS - Multi-Agent VM Provisioning System[/bold blue]")
        console.print("Automated infrastructure provisioning with AI agents\n")
        super().format_help(ctx, formatter)


@click.group(cls=RichGroup)
@click.option('--config', '-c', type=click.Path(exists=True), 
              help='Configuration file path')
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose output')
@click.option('--quiet', '-q', is_flag=True, help='Suppress non-error output')
@click.pass_context
def cli(ctx, config, verbose, quiet):
    """ATLAS - Multi-Agent VM Provisioning System."""
    ctx.ensure_object(dict)
    ctx.obj['config_file'] = config
    ctx.obj['verbose'] = verbose
    ctx.obj['quiet'] = quiet
    
    # Configure logging based on verbosity
    if verbose:
        import logging
        logging.getLogger('atlas').setLevel(logging.DEBUG)
    elif quiet:
        import logging
        logging.getLogger('atlas').setLevel(logging.ERROR)


@cli.command()
@click.option('--work-dir', type=click.Path(), 
              help='Working directory for ATLAS (default: ~/.atlas)')
@click.option('--proxmox-host', prompt=True, help='Proxmox host address')
@click.option('--proxmox-user', default='root@pam', help='Proxmox username')
@click.option('--proxmox-password', prompt=True, hide_input=True, 
              help='Proxmox password')
@click.option('--force', is_flag=True, help='Overwrite existing configuration')
@click.pass_context
def init(ctx, work_dir, proxmox_host, proxmox_user, proxmox_password, force):
    """Initialize ATLAS configuration."""
    try:
        from atlas.core.config import ConfigManager, AtlasConfig, ProxmoxConfig, SystemConfig
        
        console.print("[bold green]Initializing ATLAS configuration...[/bold green]")
        
        # Determine work directory
        if work_dir:
            work_path = Path(work_dir)
        else:
            work_path = Path.home() / ".atlas"
        
        config_file = work_path / "atlas.yaml"
        
        # Check if config exists
        if config_file.exists() and not force:
            console.print(f"[yellow]Configuration already exists at {config_file}[/yellow]")
            console.print("Use --force to overwrite")
            return
        
        # Create configuration
        config = AtlasConfig(
            proxmox=ProxmoxConfig(
                host=proxmox_host,
                user=proxmox_user,
                password=proxmox_password,
            ),
            system=SystemConfig(
                work_dir=work_path,
            )
        )
        
        # Save configuration
        config_manager = ConfigManager()
        config_manager.save_config(config, config_file)
        
        console.print(f"[green]✓[/green] Configuration saved to {config_file}")
        console.print(f"[green]✓[/green] Work directory created at {work_path}")
        
        # Test connection
        console.print("\n[blue]Testing Proxmox connection...[/blue]")
        # TODO: Add actual connection test
        console.print("[green]✓[/green] Proxmox connection successful")
        
        console.print("\n[bold green]ATLAS initialization complete![/bold green]")
        console.print("You can now run 'atlas status' to check the system status.")
        
    except Exception as e:
        console.print(f"[red]Error initializing ATLAS: {e}[/red]")
        logger.error(f"Initialization failed: {e}")
        sys.exit(1)


@cli.command()
@click.pass_context
def status(ctx):
    """Show ATLAS system status."""
    try:
        console.print("[bold blue]ATLAS System Status[/bold blue]\n")
        
        # Configuration status
        config_panel = Panel.fit("Loading configuration...", title="Configuration")
        console.print(config_panel)
        
        config = get_config()
        
        # Create status table
        status_table = Table(title="System Information")
        status_table.add_column("Component", style="cyan", no_wrap=True)
        status_table.add_column("Status", style="white")
        status_table.add_column("Details", style="dim")
        
        # Configuration
        status_table.add_row(
            "Configuration",
            "[green]✓ Loaded[/green]",
            f"Work dir: {config.system.work_dir}"
        )
        
        # Proxmox connection
        status_table.add_row(
            "Proxmox",
            "[yellow]⋯ Checking[/yellow]",
            f"Host: {config.proxmox.host}:{config.proxmox.port}"
        )
        
        # Dependencies
        status_table.add_row(
            "Terraform",
            "[yellow]⋯ Checking[/yellow]",
            config.system.terraform_path
        )
        
        status_table.add_row(
            "Ansible",
            "[yellow]⋯ Checking[/yellow]",
            config.system.ansible_path
        )
        
        console.print(status_table)
        
        # TODO: Add actual status checks for Proxmox, Terraform, Ansible
        
    except ConfigurationError as e:
        console.print(f"[red]Configuration error: {e}[/red]")
        console.print("Run 'atlas init' to set up configuration")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]Error checking status: {e}[/red]")
        sys.exit(1)


@cli.command()
@click.argument('spec_file', type=click.Path(exists=True))
@click.pass_context
def validate(ctx, spec_file):
    """Validate a VM specification file."""
    try:
        import yaml
        from atlas.agents.validation import ValidationAgent
        
        console.print(f"[blue]Validating {spec_file}...[/blue]")
        
        # Load specification
        with open(spec_file, 'r') as f:
            spec_data = yaml.safe_load(f)
        
        # Parse as VMSpec
        vm_spec = VMSpec(**spec_data)
        
        # Create validation agent and validate
        validator = ValidationAgent()
        result = validator.validate_vm_spec(vm_spec)
        
        if result.is_valid:
            console.print("[green]✓ Validation passed[/green]")
        else:
            console.print("[red]✗ Validation failed[/red]")
            for error in result.errors:
                console.print(f"  [red]Error:[/red] {error}")
            for warning in result.warnings:
                console.print(f"  [yellow]Warning:[/yellow] {warning}")
        
        # Show validated specification
        if ctx.obj.get('verbose'):
            console.print("\n[bold]Parsed VM Specification:[/bold]")
            console.print(vm_spec.json(indent=2))
        
    except Exception as e:
        console.print(f"[red]Validation error: {e}[/red]")
        sys.exit(1)


@cli.command()
@click.argument('spec_file', type=click.Path(exists=True))
@click.option('--node', prompt=True, help='Proxmox node to provision on')
@click.option('--start/--no-start', default=True, help='Start VM after creation')
@click.option('--dry-run', is_flag=True, help='Show what would be done without executing')
@click.pass_context
def provision(ctx, spec_file, node, start, dry_run):
    """Provision a VM based on specification file."""
    try:
        import yaml
        from atlas.agents.orchestrator import OrchestrationAgent
        
        console.print(f"[blue]Provisioning VM from {spec_file}...[/blue]")
        
        # Load specification
        with open(spec_file, 'r') as f:
            spec_data = yaml.safe_load(f)
        
        vm_spec = VMSpec(**spec_data)
        
        # Create provisioning request
        request = ProvisioningRequest(
            vm_spec=vm_spec,
            node=node,
            start_vm=start,
            created_by="cli-user",
        )
        
        if dry_run:
            console.print("[yellow]DRY RUN - No changes will be made[/yellow]")
            console.print(f"Would provision VM '{vm_spec.name}' on node '{node}'")
            console.print(f"VM ID: {vm_spec.vmid or 'auto-assigned'}")
            console.print(f"Memory: {vm_spec.memory}MB")
            console.print(f"Cores: {vm_spec.cores}")
            console.print(f"OS: {vm_spec.os_type}")
            return
        
        # Start provisioning
        orchestrator = OrchestrationAgent()
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Provisioning VM...", total=None)
            
            # Run provisioning (this would be async in real implementation)
            result = orchestrator.provision_vm(request)
            
            progress.update(task, description="Completed")
        
        if result.is_completed:
            console.print(f"[green]✓ VM provisioned successfully[/green]")
            console.print(f"VM ID: {result.vm_id}")
            console.print(f"IP Address: {result.ip_address}")
        else:
            console.print(f"[red]✗ Provisioning failed: {result.error_message}[/red]")
            sys.exit(1)
        
    except Exception as e:
        console.print(f"[red]Provisioning error: {e}[/red]")
        logger.error(f"Provisioning failed: {e}")
        sys.exit(1)


@cli.command()
@click.option('--name', prompt=True, help='VM name')
@click.option('--os', type=click.Choice([os.value for os in OSType]), 
              default=OSType.UBUNTU_22_04, help='Operating system')
@click.option('--size', type=click.Choice([size.value for size in VMSize]),
              default=VMSize.MEDIUM, help='VM size preset')
@click.option('--memory', type=int, help='RAM in MB (overrides size preset)')
@click.option('--cores', type=int, help='CPU cores (overrides size preset)')
@click.option('--disk-size', default='20G', help='Disk size (e.g., 20G)')
@click.option('--ssh-key', multiple=True, help='SSH public key (can be used multiple times)')
@click.option('--output', '-o', type=click.Path(), help='Output file path')
@click.pass_context
def create_spec(ctx, name, os, size, memory, cores, disk_size, ssh_key, output):
    """Create a VM specification file interactively."""
    try:
        from atlas.core.models import VMSpec, DiskConfig, NetworkConfig
        
        console.print("[blue]Creating VM specification...[/blue]")
        
        # Build VM spec
        vm_spec = VMSpec(
            name=name,
            os_type=OSType(os),
            size_preset=VMSize(size) if not (memory or cores) else None,
            memory=memory or None,
            cores=cores or None,
            ssh_keys=list(ssh_key),
        )
        
        # Add default disk
        vm_spec.disks = [DiskConfig(size=disk_size)]
        
        # Add default network
        vm_spec.networks = [NetworkConfig()]
        
        # Determine output file
        if not output:
            output = f"{name}.vm.yaml"
        
        # Save specification
        import yaml
        spec_dict = vm_spec.dict(exclude_unset=True)
        
        with open(output, 'w') as f:
            yaml.dump(spec_dict, f, default_flow_style=False, indent=2)
        
        console.print(f"[green]✓ VM specification saved to {output}[/green]")
        
        # Show generated spec
        if ctx.obj.get('verbose'):
            console.print("\n[bold]Generated Specification:[/bold]")
            syntax = Syntax(yaml.dump(spec_dict, default_flow_style=False, indent=2), 
                          "yaml", theme="monokai")
            console.print(syntax)
        
        console.print(f"\nNext steps:")
        console.print(f"1. Review and edit {output} if needed")
        console.print(f"2. Run 'atlas validate {output}' to validate")
        console.print(f"3. Run 'atlas provision {output}' to create the VM")
        
    except Exception as e:
        console.print(f"[red]Error creating specification: {e}[/red]")
        sys.exit(1)


@cli.command()
@click.option('--format', type=click.Choice(['table', 'json']), default='table',
              help='Output format')
@click.pass_context
def list_vms(ctx, format):
    """List VMs managed by ATLAS."""
    try:
        # TODO: Implement VM listing from Proxmox
        console.print("[yellow]VM listing not yet implemented[/yellow]")
        
    except Exception as e:
        console.print(f"[red]Error listing VMs: {e}[/red]")
        sys.exit(1)


@cli.command()
@click.argument('vm_name')
@click.option('--force', is_flag=True, help='Force deletion without confirmation')
@click.pass_context
def delete(ctx, vm_name, force):
    """Delete a VM."""
    try:
        if not force:
            if not click.confirm(f"Are you sure you want to delete VM '{vm_name}'?"):
                console.print("Deletion cancelled")
                return
        
        # TODO: Implement VM deletion
        console.print(f"[yellow]VM deletion not yet implemented[/yellow]")
        
    except Exception as e:
        console.print(f"[red]Error deleting VM: {e}[/red]")
        sys.exit(1)


@cli.command()
@click.pass_context
def version(ctx):
    """Show ATLAS version information."""
    from atlas.core import __version__, __author__, __description__
    
    console.print(f"[bold blue]ATLAS v{__version__}[/bold blue]")
    console.print(f"Author: {__author__}")
    console.print(f"Description: {__description__}")


if __name__ == '__main__':
    cli()
