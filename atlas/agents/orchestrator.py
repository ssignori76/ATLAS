"""
Orchestration agent for the ATLAS system.

This agent coordinates the entire VM provisioning workflow, managing
the interaction between different agents and ensuring proper execution
of all provisioning steps.
"""

import asyncio
import uuid
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum

from atlas.core import (
    get_logger,
    WorkflowError,
    AgentError,
    ProvisioningRequest,
    ProvisioningResult,
    ProvisioningStatus,
    WorkflowStep,
    WorkflowConfig,
    VMSpec,
)
from .base import BaseAgent, AgentCapabilities, AgentMessage, MessageType
from .data_collector import DataCollectorAgent
from .validation import ValidationAgent


class WorkflowStepStatus(str, Enum):
    """Workflow step status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class WorkflowExecution:
    """Workflow execution tracking."""
    
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    request: ProvisioningRequest = None
    config: WorkflowConfig = None
    status: ProvisioningStatus = ProvisioningStatus.PENDING
    current_step: Optional[str] = None
    step_status: Dict[str, WorkflowStepStatus] = field(default_factory=dict)
    step_results: Dict[str, Any] = field(default_factory=dict)
    step_errors: Dict[str, str] = field(default_factory=dict)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    logs: List[str] = field(default_factory=list)


class OrchestrationAgent(BaseAgent):
    """Agent responsible for orchestrating VM provisioning workflows."""
    
    def __init__(self, agent_id: Optional[str] = None, config: Optional[Dict[str, Any]] = None):
        """Initialize the orchestration agent."""
        super().__init__(agent_id, config)
        
        # Active workflow executions
        self._executions: Dict[str, WorkflowExecution] = {}
        
        # Agent registry
        self._agents: Dict[str, BaseAgent] = {}
        
        # Default workflow configurations
        self._workflow_templates: Dict[str, WorkflowConfig] = {}
        self._setup_default_workflows()
    
    def _get_capabilities(self) -> AgentCapabilities:
        """Get agent capabilities."""
        return AgentCapabilities(
            name="OrchestrationAgent",
            version="1.0.0",
            description="Orchestrates VM provisioning workflows",
            supported_operations=[
                "provision_vm",
                "create_workflow",
                "execute_workflow",
                "monitor_workflow",
                "cancel_workflow",
                "get_status",
                "list_workflows",
            ],
            input_types=["ProvisioningRequest", "WorkflowConfig", "dict"],
            output_types=["ProvisioningResult", "WorkflowExecution"],
            dependencies=["data_collector", "validation", "terraform_generator", "ansible_generator"],
            resource_requirements={"memory": "1GB", "cpu": "0.5"},
            concurrent_requests=3,
        )
    
    async def process_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Process orchestration request."""
        operation = request.get('operation')
        
        if operation == 'provision_vm':
            return await self._provision_vm_request(request)
        elif operation == 'create_workflow':
            return await self._create_workflow_request(request)
        elif operation == 'execute_workflow':
            return await self._execute_workflow_request(request)
        elif operation == 'monitor_workflow':
            return await self._monitor_workflow_request(request)
        elif operation == 'cancel_workflow':
            return await self._cancel_workflow_request(request)
        elif operation == 'get_status':
            return await self._get_status_request(request)
        else:
            raise WorkflowError(f"Unknown orchestration operation: {operation}")
    
    async def provision_vm(self, request: ProvisioningRequest) -> ProvisioningResult:
        """Provision a VM using the standard workflow.
        
        Args:
            request: Provisioning request
            
        Returns:
            Provisioning result
        """
        self.logger.info(f"Starting VM provisioning: {request.vm_spec.name}")
        
        # Create workflow execution
        execution = WorkflowExecution(
            request=request,
            config=self._workflow_templates['standard_provision'],
        )
        
        self._executions[execution.id] = execution
        
        try:
            # Execute workflow
            result = await self._execute_workflow(execution)
            return result
            
        except Exception as e:
            execution.status = ProvisioningStatus.FAILED
            execution.error_message = str(e)
            execution.completed_at = datetime.utcnow()
            
            self.logger.error(f"VM provisioning failed: {e}")
            raise
        
        finally:
            # Keep execution for history (could implement cleanup later)
            pass
    
    async def _execute_workflow(self, execution: WorkflowExecution) -> ProvisioningResult:
        """Execute a workflow.
        
        Args:
            execution: Workflow execution to run
            
        Returns:
            Provisioning result
        """
        execution.status = ProvisioningStatus.RUNNING
        execution.started_at = datetime.utcnow()
        
        self.logger.info(f"Executing workflow {execution.config.name} for {execution.request.vm_spec.name}")
        
        try:
            # Initialize step status
            for step in execution.config.steps:
                execution.step_status[step.name] = WorkflowStepStatus.PENDING
            
            # Execute steps
            for step in execution.config.steps:
                await self._execute_step(execution, step)
                
                # Check if we should continue
                if execution.status == ProvisioningStatus.FAILED and execution.config.fail_fast:
                    break
            
            # Create result
            if execution.status == ProvisioningStatus.RUNNING:
                execution.status = ProvisioningStatus.COMPLETED
                execution.completed_at = datetime.utcnow()
            
            result = self._create_provisioning_result(execution)
            
            self.logger.info(f"Workflow completed with status: {execution.status}")
            return result
            
        except Exception as e:
            execution.status = ProvisioningStatus.FAILED
            execution.error_message = str(e)
            execution.completed_at = datetime.utcnow()
            raise WorkflowError(f"Workflow execution failed: {e}", workflow=execution.config.name)
    
    async def _execute_step(self, execution: WorkflowExecution, step: WorkflowStep) -> None:
        """Execute a single workflow step.
        
        Args:
            execution: Current workflow execution
            step: Step to execute
        """
        self.logger.info(f"Executing step: {step.name}")
        
        execution.current_step = step.name
        execution.step_status[step.name] = WorkflowStepStatus.RUNNING
        
        # Add to logs
        execution.logs.append(f"Starting step: {step.name}")
        
        try:
            # Check dependencies
            await self._check_step_dependencies(execution, step)
            
            # Execute step based on agent
            if step.agent == 'data_collector':
                result = await self._execute_data_collector_step(execution, step)
            elif step.agent == 'validation':
                result = await self._execute_validation_step(execution, step)
            elif step.agent == 'terraform_generator':
                result = await self._execute_terraform_generator_step(execution, step)
            elif step.agent == 'ansible_generator':
                result = await self._execute_ansible_generator_step(execution, step)
            elif step.agent == 'provisioner':
                result = await self._execute_provisioner_step(execution, step)
            else:
                raise WorkflowError(f"Unknown agent for step {step.name}: {step.agent}")
            
            # Store result
            execution.step_results[step.name] = result
            execution.step_status[step.name] = WorkflowStepStatus.COMPLETED
            execution.logs.append(f"Completed step: {step.name}")
            
        except Exception as e:
            execution.step_status[step.name] = WorkflowStepStatus.FAILED
            execution.step_errors[step.name] = str(e)
            execution.logs.append(f"Failed step {step.name}: {e}")
            
            # Handle retries
            if step.retry_count < step.max_retries:
                step.retry_count += 1
                self.logger.warning(f"Retrying step {step.name} (attempt {step.retry_count})")
                await asyncio.sleep(2 ** step.retry_count)  # Exponential backoff
                await self._execute_step(execution, step)
            else:
                execution.status = ProvisioningStatus.FAILED
                raise WorkflowError(f"Step {step.name} failed: {e}", step=step.name)
    
    async def _check_step_dependencies(self, execution: WorkflowExecution, step: WorkflowStep) -> None:
        """Check if step dependencies are satisfied."""
        for dep in step.depends_on:
            if dep not in execution.step_status:
                raise WorkflowError(f"Step {step.name} depends on unknown step: {dep}")
            
            if execution.step_status[dep] != WorkflowStepStatus.COMPLETED:
                raise WorkflowError(f"Step {step.name} dependency not satisfied: {dep}")
    
    async def _execute_data_collector_step(self, execution: WorkflowExecution, 
                                         step: WorkflowStep) -> Dict[str, Any]:
        """Execute data collector step."""
        # For now, we assume data is already collected in the request
        # In a real implementation, this might validate or enrich the data
        
        return {
            'vm_spec': execution.request.vm_spec.dict(),
            'collection_method': 'request',
        }
    
    async def _execute_validation_step(self, execution: WorkflowExecution, 
                                     step: WorkflowStep) -> Dict[str, Any]:
        """Execute validation step."""
        self.logger.debug("Executing validation step")
        
        # Create validation agent if not exists
        if 'validation' not in self._agents:
            self._agents['validation'] = ValidationAgent()
        
        validator = self._agents['validation']
        
        # Validate VM specification
        validation_result = await validator.validate_vm_spec(execution.request.vm_spec)
        
        if not validation_result.is_valid:
            raise WorkflowError(f"Validation failed: {'; '.join(validation_result.errors)}")
        
        return {
            'validation_result': validation_result.dict(),
        }
    
    async def _execute_terraform_generator_step(self, execution: WorkflowExecution, 
                                              step: WorkflowStep) -> Dict[str, Any]:
        """Execute Terraform generator step."""
        self.logger.debug("Executing Terraform generator step")
        
        # TODO: Implement Terraform generation
        # This would create Terraform configuration files
        
        terraform_config = f"""
# Generated Terraform configuration for {execution.request.vm_spec.name}
resource "proxmox_vm_qemu" "{execution.request.vm_spec.name}" {{
  name         = "{execution.request.vm_spec.name}"
  target_node  = "{execution.request.node}"
  memory       = {execution.request.vm_spec.memory}
  cores        = {execution.request.vm_spec.cores}
  sockets      = {execution.request.vm_spec.sockets}
  
  # Additional configuration would be generated here
}}
"""
        
        return {
            'terraform_config': terraform_config,
            'config_file': f"{execution.request.vm_spec.name}.tf",
        }
    
    async def _execute_ansible_generator_step(self, execution: WorkflowExecution, 
                                            step: WorkflowStep) -> Dict[str, Any]:
        """Execute Ansible generator step."""
        self.logger.debug("Executing Ansible generator step")
        
        # TODO: Implement Ansible playbook generation
        # This would create Ansible playbooks for configuration
        
        ansible_playbook = f"""
---
- name: Configure {execution.request.vm_spec.name}
  hosts: {execution.request.vm_spec.name}
  become: yes
  tasks:
    - name: Update system packages
      package:
        name: '*'
        state: latest
      when: ansible_os_family == "RedHat" or ansible_os_family == "Debian"
    
    # Additional tasks would be generated here
"""
        
        return {
            'ansible_playbook': ansible_playbook,
            'playbook_file': f"{execution.request.vm_spec.name}.yml",
        }
    
    async def _execute_provisioner_step(self, execution: WorkflowExecution, 
                                      step: WorkflowStep) -> Dict[str, Any]:
        """Execute provisioner step."""
        self.logger.debug("Executing provisioner step")
        
        # TODO: Implement actual Proxmox provisioning
        # This would use the Proxmox API to create the VM
        
        # Simulate VM creation
        vm_id = execution.request.vm_spec.vmid or 100  # Would be auto-assigned
        ip_address = "192.168.1.100"  # Would be obtained from VM
        
        # Simulate some delay
        await asyncio.sleep(2)
        
        return {
            'vm_id': vm_id,
            'ip_address': ip_address,
            'status': 'running',
        }
    
    def _create_provisioning_result(self, execution: WorkflowExecution) -> ProvisioningResult:
        """Create provisioning result from execution."""
        # Extract key information from step results
        vm_id = None
        ip_address = None
        terraform_config = None
        ansible_playbook = None
        
        for step_name, result in execution.step_results.items():
            if 'vm_id' in result:
                vm_id = result['vm_id']
            if 'ip_address' in result:
                ip_address = result['ip_address']
            if 'terraform_config' in result:
                terraform_config = result['terraform_config']
            if 'ansible_playbook' in result:
                ansible_playbook = result['ansible_playbook']
        
        return ProvisioningResult(
            request_id=execution.id,
            vm_spec=execution.request.vm_spec,
            status=execution.status,
            vm_id=vm_id,
            ip_address=ip_address,
            node=execution.request.node,
            created_at=execution.started_at or datetime.utcnow(),
            started_at=execution.started_at,
            completed_at=execution.completed_at,
            error_message=execution.error_message,
            terraform_config=terraform_config,
            ansible_playbook=ansible_playbook,
            logs=execution.logs,
        )
    
    def _setup_default_workflows(self) -> None:
        """Setup default workflow templates."""
        # Standard VM provisioning workflow
        standard_steps = [
            WorkflowStep(
                name="validate_specification",
                agent="validation",
                inputs={},
                depends_on=[],
                timeout=60,
            ),
            WorkflowStep(
                name="generate_terraform",
                agent="terraform_generator",
                inputs={},
                depends_on=["validate_specification"],
                timeout=120,
            ),
            WorkflowStep(
                name="generate_ansible",
                agent="ansible_generator",
                inputs={},
                depends_on=["validate_specification"],
                timeout=120,
            ),
            WorkflowStep(
                name="provision_vm",
                agent="provisioner",
                inputs={},
                depends_on=["generate_terraform"],
                timeout=600,
            ),
            WorkflowStep(
                name="configure_vm",
                agent="ansible_executor",
                inputs={},
                depends_on=["provision_vm", "generate_ansible"],
                timeout=900,
            ),
        ]
        
        self._workflow_templates['standard_provision'] = WorkflowConfig(
            name="standard_provision",
            description="Standard VM provisioning workflow",
            steps=standard_steps,
            parallel_execution=True,
            fail_fast=True,
            timeout=3600,
        )
        
        # Quick provision workflow (no configuration)
        quick_steps = [
            WorkflowStep(
                name="validate_specification",
                agent="validation",
                inputs={},
                depends_on=[],
                timeout=60,
            ),
            WorkflowStep(
                name="generate_terraform",
                agent="terraform_generator",
                inputs={},
                depends_on=["validate_specification"],
                timeout=120,
            ),
            WorkflowStep(
                name="provision_vm",
                agent="provisioner",
                inputs={},
                depends_on=["generate_terraform"],
                timeout=600,
            ),
        ]
        
        self._workflow_templates['quick_provision'] = WorkflowConfig(
            name="quick_provision",
            description="Quick VM provisioning without configuration",
            steps=quick_steps,
            parallel_execution=True,
            fail_fast=True,
            timeout=1800,
        )
    
    async def _provision_vm_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle VM provisioning request."""
        try:
            vm_spec_data = request.get('vm_spec')
            vm_spec = VMSpec(**vm_spec_data) if isinstance(vm_spec_data, dict) else vm_spec_data
            
            provisioning_request = ProvisioningRequest(
                vm_spec=vm_spec,
                node=request.get('node', 'pve'),
                start_vm=request.get('start_vm', True),
                created_by=request.get('created_by', 'unknown'),
            )
            
            result = await self.provision_vm(provisioning_request)
            
            return {
                'success': True,
                'result': result.dict(),
            }
        
        except Exception as e:
            self.logger.error(f"VM provisioning request failed: {e}")
            return {
                'success': False,
                'error': str(e),
            }
    
    async def _create_workflow_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle workflow creation request."""
        # Implementation for creating custom workflows
        return {'success': True, 'message': 'Workflow creation not yet implemented'}
    
    async def _execute_workflow_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle workflow execution request."""
        # Implementation for executing custom workflows
        return {'success': True, 'message': 'Custom workflow execution not yet implemented'}
    
    async def _monitor_workflow_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle workflow monitoring request."""
        execution_id = request.get('execution_id')
        
        if execution_id not in self._executions:
            return {
                'success': False,
                'error': f'Execution not found: {execution_id}',
            }
        
        execution = self._executions[execution_id]
        
        return {
            'success': True,
            'execution': {
                'id': execution.id,
                'status': execution.status.value,
                'current_step': execution.current_step,
                'step_status': {k: v.value for k, v in execution.step_status.items()},
                'started_at': execution.started_at.isoformat() if execution.started_at else None,
                'completed_at': execution.completed_at.isoformat() if execution.completed_at else None,
                'logs': execution.logs[-10:],  # Last 10 log entries
            },
        }
    
    async def _cancel_workflow_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle workflow cancellation request."""
        execution_id = request.get('execution_id')
        
        if execution_id not in self._executions:
            return {
                'success': False,
                'error': f'Execution not found: {execution_id}',
            }
        
        execution = self._executions[execution_id]
        
        if execution.status in [ProvisioningStatus.COMPLETED, ProvisioningStatus.FAILED]:
            return {
                'success': False,
                'error': 'Cannot cancel completed or failed workflow',
            }
        
        execution.status = ProvisioningStatus.CANCELLED
        execution.completed_at = datetime.utcnow()
        execution.logs.append("Workflow cancelled by user")
        
        return {
            'success': True,
            'message': 'Workflow cancelled',
        }
    
    async def _get_status_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle status request."""
        return {
            'success': True,
            'status': {
                'active_executions': len([e for e in self._executions.values() 
                                        if e.status == ProvisioningStatus.RUNNING]),
                'total_executions': len(self._executions),
                'available_workflows': list(self._workflow_templates.keys()),
                'registered_agents': list(self._agents.keys()),
            },
        }
