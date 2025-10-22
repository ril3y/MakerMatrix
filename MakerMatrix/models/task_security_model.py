"""
Task Security Model - Defines permissions and restrictions for different task types
"""

from enum import Enum
from typing import Dict, List, Optional
from dataclasses import dataclass
from MakerMatrix.models.task_models import TaskType


class TaskSecurityLevel(str, Enum):
    """Security levels for tasks"""
    PUBLIC = "public"           # Any authenticated user
    USER = "user"              # Regular users with task permissions  
    POWER_USER = "power_user"  # Users with elevated task permissions
    ADMIN = "admin"            # Admin-only tasks
    SYSTEM = "system"          # System-only tasks (automated)


class TaskRiskLevel(str, Enum):
    """Risk levels for tasks"""
    LOW = "low"         # Safe operations (read-only, local)
    MEDIUM = "medium"   # Moderate risk (data modification, limited external calls)
    HIGH = "high"       # High risk (bulk operations, expensive external calls)
    CRITICAL = "critical"  # Critical operations (system changes, data deletion)


@dataclass
class TaskSecurityPolicy:
    """Security policy for a specific task type"""
    security_level: TaskSecurityLevel
    risk_level: TaskRiskLevel
    required_permissions: List[str]
    max_concurrent_per_user: int = 1
    rate_limit_per_hour: Optional[int] = None
    rate_limit_per_day: Optional[int] = None
    requires_approval: bool = False
    audit_level: str = "standard"  # "none", "standard", "detailed"
    resource_limits: Dict[str, int] = None
    
    def __post_init__(self):
        if self.resource_limits is None:
            self.resource_limits = {}


# Task Security Policies Registry
TASK_SECURITY_POLICIES: Dict[TaskType, TaskSecurityPolicy] = {
    
    # =============== USER-LEVEL TASKS ===============
    TaskType.PART_ENRICHMENT: TaskSecurityPolicy(
        security_level=TaskSecurityLevel.USER,
        risk_level=TaskRiskLevel.MEDIUM,
        required_permissions=["parts:write", "tasks:user"],
        max_concurrent_per_user=3,    # Allow 3 concurrent enrichments
        rate_limit_per_hour=30,       # Up to 30 single enrichments per hour
        rate_limit_per_day=150,       # Up to 150 single enrichments per day
        audit_level="detailed",
        resource_limits={"max_parts": 1, "max_capabilities": 5}
    ),
    
    TaskType.DATASHEET_FETCH: TaskSecurityPolicy(
        security_level=TaskSecurityLevel.USER,
        risk_level=TaskRiskLevel.LOW,
        required_permissions=["parts:write", "tasks:user"],
        max_concurrent_per_user=3,
        rate_limit_per_hour=20,
        rate_limit_per_day=100,
        audit_level="standard",
        resource_limits={"max_parts": 1}
    ),
    
    TaskType.IMAGE_FETCH: TaskSecurityPolicy(
        security_level=TaskSecurityLevel.USER,
        risk_level=TaskRiskLevel.LOW,
        required_permissions=["parts:write", "tasks:user"],
        max_concurrent_per_user=3,
        rate_limit_per_hour=15,
        rate_limit_per_day=75,
        audit_level="standard",
        resource_limits={"max_parts": 1}
    ),
    
    # =============== POWER USER TASKS ===============
    TaskType.BULK_ENRICHMENT: TaskSecurityPolicy(
        security_level=TaskSecurityLevel.POWER_USER,
        risk_level=TaskRiskLevel.HIGH,
        required_permissions=["parts:write", "tasks:power_user"],
        max_concurrent_per_user=2,    # Allow 2 concurrent bulk operations
        rate_limit_per_hour=50,       # Up to 50 bulk operations per hour
        rate_limit_per_day=200,       # Up to 200 bulk operations per day
        audit_level="detailed",
        resource_limits={"max_parts": 50, "batch_size": 10}  # 50 parts per operation
    ),
    
    TaskType.FILE_IMPORT_ENRICHMENT: TaskSecurityPolicy(
        security_level=TaskSecurityLevel.POWER_USER,
        risk_level=TaskRiskLevel.HIGH,
        required_permissions=["parts:write", "csv:import", "tasks:power_user"],
        max_concurrent_per_user=2,    # Allow 2 concurrent imports
        rate_limit_per_hour=20,       # Up to 20 file imports per hour
        rate_limit_per_day=100,       # Up to 100 file imports per day
        audit_level="detailed",
        resource_limits={"max_parts": 1000}  # Support larger imports
    ),
    
    TaskType.PRICE_UPDATE: TaskSecurityPolicy(
        security_level=TaskSecurityLevel.POWER_USER,
        risk_level=TaskRiskLevel.MEDIUM,
        required_permissions=["parts:write", "pricing:update", "tasks:power_user"],
        max_concurrent_per_user=1,
        rate_limit_per_hour=5,
        rate_limit_per_day=20,
        audit_level="detailed"
    ),
    
    # =============== ADMIN-ONLY TASKS ===============
    TaskType.DATABASE_CLEANUP: TaskSecurityPolicy(
        security_level=TaskSecurityLevel.ADMIN,
        risk_level=TaskRiskLevel.CRITICAL,
        required_permissions=["admin", "database:cleanup", "tasks:admin"],
        max_concurrent_per_user=1,
        rate_limit_per_hour=1,
        rate_limit_per_day=3,
        requires_approval=False,  # Could be True for extra safety
        audit_level="detailed"
    ),
    
    TaskType.BACKUP_CREATION: TaskSecurityPolicy(
        security_level=TaskSecurityLevel.ADMIN,
        risk_level=TaskRiskLevel.HIGH,
        required_permissions=["admin", "backup:create", "tasks:admin"],
        max_concurrent_per_user=1,
        rate_limit_per_hour=2,
        rate_limit_per_day=5,
        audit_level="detailed"
    ),
    
    # =============== SYSTEM TASKS =============== 
    TaskType.INVENTORY_AUDIT: TaskSecurityPolicy(
        security_level=TaskSecurityLevel.SYSTEM,
        risk_level=TaskRiskLevel.LOW,
        required_permissions=["system", "inventory:audit"],
        max_concurrent_per_user=1,
        audit_level="standard"
    ),
    
    TaskType.DATA_SYNC: TaskSecurityPolicy(
        security_level=TaskSecurityLevel.SYSTEM,
        risk_level=TaskRiskLevel.MEDIUM,
        required_permissions=["system", "data:sync"],
        max_concurrent_per_user=1,
        audit_level="detailed"
    ),
    
    # =============== GENERAL TASKS ===============
    TaskType.PART_VALIDATION: TaskSecurityPolicy(
        security_level=TaskSecurityLevel.USER,
        risk_level=TaskRiskLevel.LOW,
        required_permissions=["parts:read", "tasks:user"],
        max_concurrent_per_user=2,
        rate_limit_per_hour=20,
        audit_level="standard"
    ),
    
    TaskType.REPORT_GENERATION: TaskSecurityPolicy(
        security_level=TaskSecurityLevel.USER,
        risk_level=TaskRiskLevel.LOW,
        required_permissions=["reports:generate", "tasks:user"],
        max_concurrent_per_user=2,
        rate_limit_per_hour=10,
        rate_limit_per_day=50,
        audit_level="standard"
    ),
}


def get_task_security_policy(task_type: TaskType) -> Optional[TaskSecurityPolicy]:
    """Get security policy for a task type"""
    return TASK_SECURITY_POLICIES.get(task_type)


def get_user_allowed_task_types(user_permissions: List[str]) -> List[TaskType]:
    """Get task types a user is allowed to create based on their permissions"""
    allowed_tasks = []
    
    for task_type, policy in TASK_SECURITY_POLICIES.items():
        # Check if user has all required permissions
        if all(perm in user_permissions for perm in policy.required_permissions):
            allowed_tasks.append(task_type)
    
    return allowed_tasks


def is_task_allowed_for_user(task_type: TaskType, user_permissions: List[str]) -> bool:
    """Check if a user can create a specific task type"""
    policy = get_task_security_policy(task_type)
    if not policy:
        return False
    
    return all(perm in user_permissions for perm in policy.required_permissions)


def get_task_security_summary() -> Dict[str, List[str]]:
    """Get summary of tasks by security level"""
    summary = {
        "public": [],
        "user": [],
        "power_user": [],
        "admin": [],
        "system": []
    }
    
    for task_type, policy in TASK_SECURITY_POLICIES.items():
        summary[policy.security_level.value].append(task_type.value)
    
    return summary