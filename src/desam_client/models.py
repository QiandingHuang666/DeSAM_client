"""DeSAM客户端数据模型"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional


@dataclass
class Resource:
    """资源需求"""

    cpu: int = 1
    memory_mb: int = 1024
    gpu: int = 0
    disk_mb: int = 0


@dataclass
class Job:
    """作业信息"""

    job_id: str
    user_id: str
    name: str
    command: str
    status: str
    resources: Resource = field(default_factory=Resource)
    working_dir: Optional[str] = None
    env: Optional[Dict[str, str]] = None
    timeout: Optional[int] = None
    retries: int = 0
    artifacts: Optional[List[str]] = None
    labels: Optional[Dict[str, str]] = None
    description: Optional[str] = None
    metadata: Optional[Dict[str, str]] = None
    submit_time: Optional[datetime] = None
    start_time: Optional[datetime] = None
    finish_time: Optional[datetime] = None
    error_message: Optional[str] = None
    executor_id: Optional[str] = None

    @classmethod
    def from_proto(cls, proto_job) -> "Job":
        """从protobuf Job对象创建Job实例"""
        return cls(
            job_id=proto_job.job_id,
            user_id=proto_job.user_id,
            name=proto_job.name,
            command=proto_job.command,
            status=_status_name(proto_job.status),
            resources=Resource(
                cpu=proto_job.resources.cpu_cores,
                memory_mb=proto_job.resources.memory_mb,
                gpu=proto_job.resources.gpu_count,
                disk_mb=proto_job.resources.disk_mb,
            ),
            working_dir=proto_job.working_dir or None,
            env=dict(proto_job.env) if hasattr(proto_job, 'env') else None,
            timeout=proto_job.timeout if proto_job.timeout > 0 else None,
            retries=proto_job.retries,
            artifacts=list(proto_job.artifacts) if proto_job.artifacts else None,
            labels=dict(proto_job.labels) if hasattr(proto_job, 'labels') and proto_job.labels else None,
            description=proto_job.description or None,
            metadata=dict(proto_job.metadata) if hasattr(proto_job, 'metadata') and proto_job.metadata else None,
            submit_time=(
                datetime.fromtimestamp(proto_job.submit_time)
                if proto_job.submit_time
                else None
            ),
            start_time=(
                datetime.fromtimestamp(proto_job.start_time)
                if proto_job.start_time
                else None
            ),
            finish_time=(
                datetime.fromtimestamp(proto_job.finish_time)
                if proto_job.finish_time
                else None
            ),
            error_message=proto_job.error_message or None,
            executor_id=proto_job.executor_id or None,
        )


# 状态枚举值到名称的映射
_STATUS_NAMES = {
    0: "UNKNOWN",
    1: "QUEUED",
    2: "PREPARING",
    3: "RUNNING",
    4: "SUCCEEDED",
    5: "FAILED",
    6: "CANCELLED",
    7: "TIMEOUT",
}


def _status_name(status_value: int) -> str:
    """将状态枚举值转换为名称"""
    return _STATUS_NAMES.get(status_value, "UNKNOWN")
