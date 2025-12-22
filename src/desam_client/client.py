"""DeSAM客户端主类"""

from typing import Dict, List, Optional

import grpc

# 导入生成的gRPC代码
from ._grpc import client_pb2, client_pb2_grpc
from .exceptions import (
    AuthenticationError,
    DeSAMConnectionError,
    DeSAMError,
    JobNotFoundError,
    SubmitError,
)
from .models import Job, Resource
from .file_transfer import FileManager


class DeSAMClient:
    """DeSAM调度器客户端

    用于与DeSAM调度器进行通信，支持作业提交、查询、取消等操作。

    示例:
        ```python
        client = DeSAMClient(
            host="192.168.1.100",
            port=50051,
            api_key="sk-your-api-key"
        )

        job_id = client.submit_job(
            name="训练任务",
            command="python train.py",
            cpu=4,
            memory_mb=8192
        )

        status = client.get_status(job_id)
        client.close()
        ```
    """

    def __init__(
        self,
        host: str,
        port: int = 50051,
        api_key: str = "",
        cert_path: Optional[str] = None,
        timeout: float = 30.0,
    ):
        """初始化DeSAM客户端

        Args:
            host: 调度器地址
            port: 调度器端口（默认50051）
            api_key: API Key
            cert_path: TLS证书路径（可选，生产环境建议使用）
            timeout: 请求超时时间（秒，默认30）
        """
        self.host = host
        self.port = port
        self.api_key = api_key
        self.cert_path = cert_path
        self.timeout = timeout

        self._channel = None
        self._stub = None
        self._connect()

        # 初始化文件传输管理器
        self.files = FileManager(self)

    def _connect(self):
        """建立gRPC连接"""
        try:
            target = f"{self.host}:{self.port}"

            if self.cert_path:
                # TLS安全连接
                with open(self.cert_path, "rb") as f:
                    creds = grpc.ssl_channel_credentials(f.read())
                self._channel = grpc.secure_channel(target, creds)
            else:
                # 非安全连接（仅开发环境）
                self._channel = grpc.insecure_channel(target)

            self._stub = client_pb2_grpc.ClientServiceStub(self._channel)

        except Exception as e:
            raise DeSAMConnectionError(f"连接调度器失败: {e}")

    def submit_job(
        self,
        name: str,
        command: str,
        cpu: int = 1,
        memory_mb: int = 1024,
        gpu: int = 0,
        disk_mb: int = 0,
        working_dir: Optional[str] = None,
        env: Optional[Dict[str, str]] = None,
        timeout: Optional[int] = None,
        retries: int = 0,
        artifacts: Optional[List[str]] = None,
        labels: Optional[Dict[str, str]] = None,
        description: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
        user_id: Optional[str] = None,
    ) -> str:
        """提交作业

        Args:
            name: 作业名称
            command: 执行命令
            cpu: CPU核心数（默认1）
            memory_mb: 内存大小MB（默认1024）
            gpu: GPU数量（默认0）
            disk_mb: 磁盘空间MB（默认0）
            working_dir: 工作目录（可选）
            env: 环境变量（可选）
            timeout: 超时时间秒（可选）
            retries: 重试次数（默认0）
            artifacts: 数据依赖文件列表（可选）
            labels: 标签（可选）
            description: 描述（可选）
            metadata: 元数据（可选）
            user_id: 用户ID（可选，默认从API Key解析）

        Returns:
            str: 作业ID

        Raises:
            AuthenticationError: API Key无效
            SubmitError: 提交失败
        """
        request = client_pb2.SubmitJobRequest(
            api_key=self.api_key,
            user_id=user_id or "default_user",
            name=name,
            command=command,
            working_dir=working_dir or "",
            resources=client_pb2.ResourceRequirement(
                cpu_cores=cpu,
                memory_mb=memory_mb,
                gpu_count=gpu,
                disk_mb=disk_mb,
            ),
            env=env or {},
            timeout=timeout or 0,
            retries=retries,
            artifacts=artifacts or [],
            labels=labels or {},
            description=description or "",
            metadata=metadata or {},
        )

        try:
            response = self._stub.SubmitJob(request, timeout=self.timeout)

            if not response.response.success:
                if response.response.error_code == "INVALID_API_KEY":
                    raise AuthenticationError("API Key无效")
                raise SubmitError(response.response.message)

            return response.job_id

        except grpc.RpcError as e:
            raise DeSAMConnectionError(f"gRPC调用失败: {e}")

    def get_status(self, job_id: str) -> str:
        """获取作业状态

        Args:
            job_id: 作业ID

        Returns:
            str: 作业状态（QUEUED/PREPARING/RUNNING/SUCCEEDED/FAILED/CANCELLED/TIMEOUT）

        Raises:
            AuthenticationError: API Key无效
            JobNotFoundError: 作业不存在
        """
        job = self.get_info(job_id)
        return job.status

    def get_info(self, job_id: str) -> Job:
        """获取作业完整信息

        Args:
            job_id: 作业ID

        Returns:
            Job: 作业信息对象

        Raises:
            AuthenticationError: API Key无效
            JobNotFoundError: 作业不存在
        """
        request = client_pb2.QueryJobRequest(
            api_key=self.api_key,
            job_id=job_id,
        )

        try:
            response = self._stub.QueryJob(request, timeout=self.timeout)

            if not response.response.success:
                if response.response.error_code == "INVALID_API_KEY":
                    raise AuthenticationError("API Key无效")
                if response.response.error_code == "JOB_NOT_FOUND":
                    raise JobNotFoundError(f"作业不存在: {job_id}")
                raise DeSAMError(response.response.message)

            return Job.from_proto(response.job)

        except grpc.RpcError as e:
            raise DeSAMConnectionError(f"gRPC调用失败: {e}")

    def list_jobs(
        self,
        user_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Job]:
        """列出作业

        Args:
            user_id: 按用户ID过滤（可选）
            status: 按状态过滤（可选）
            limit: 返回数量限制（默认100）
            offset: 偏移量（分页用）

        Returns:
            List[Job]: 作业列表

        Raises:
            AuthenticationError: API Key无效
        """
        # 状态名称到枚举值的映射
        status_map = {
            "UNKNOWN": 0,
            "QUEUED": 1,
            "PREPARING": 2,
            "RUNNING": 3,
            "SUCCEEDED": 4,
            "FAILED": 5,
            "CANCELLED": 6,
            "TIMEOUT": 7,
        }

        request = client_pb2.ListJobsRequest(
            api_key=self.api_key,
            user_id=user_id or "",
            status=status_map.get(status, 0) if status else 0,
            limit=limit,
            offset=offset,
        )

        try:
            response = self._stub.ListJobs(request, timeout=self.timeout)

            if not response.response.success:
                if response.response.error_code == "INVALID_API_KEY":
                    raise AuthenticationError("API Key无效")
                raise DeSAMError(response.response.message)

            return [Job.from_proto(j) for j in response.jobs]

        except grpc.RpcError as e:
            raise DeSAMConnectionError(f"gRPC调用失败: {e}")

    def cancel(self, job_id: str) -> bool:
        """取消作业

        Args:
            job_id: 作业ID

        Returns:
            bool: 是否成功取消

        Raises:
            AuthenticationError: API Key无效
            JobNotFoundError: 作业不存在
        """
        request = client_pb2.CancelJobRequest(
            api_key=self.api_key,
            job_id=job_id,
        )

        try:
            response = self._stub.CancelJob(request, timeout=self.timeout)

            if not response.response.success:
                if response.response.error_code == "INVALID_API_KEY":
                    raise AuthenticationError("API Key无效")
                if response.response.error_code == "JOB_NOT_FOUND":
                    raise JobNotFoundError(f"作业不存在: {job_id}")
                return False

            return True

        except grpc.RpcError as e:
            raise DeSAMConnectionError(f"gRPC调用失败: {e}")

    def batch_get_info(self, job_ids: List[str]) -> List[Job]:
        """批量获取作业信息

        Args:
            job_ids: 作业ID列表

        Returns:
            List[Job]: 作业信息列表

        Raises:
            AuthenticationError: API Key无效
        """
        request = client_pb2.BatchQueryJobsRequest(
            api_key=self.api_key,
            job_ids=job_ids,
        )

        try:
            response = self._stub.BatchQueryJobs(request, timeout=self.timeout)

            if not response.response.success:
                if response.response.error_code == "INVALID_API_KEY":
                    raise AuthenticationError("API Key无效")
                raise DeSAMError(response.response.message)

            return [Job.from_proto(j) for j in response.jobs]

        except grpc.RpcError as e:
            raise DeSAMConnectionError(f"gRPC调用失败: {e}")

    def batch_cancel(self, job_ids: List[str]) -> Dict[str, bool]:
        """批量取消作业

        Args:
            job_ids: 作业ID列表

        Returns:
            Dict[str, bool]: 各作业的取消结果 {job_id: success}

        Raises:
            AuthenticationError: API Key无效
        """
        request = client_pb2.BatchCancelJobsRequest(
            api_key=self.api_key,
            job_ids=job_ids,
        )

        try:
            response = self._stub.BatchCancelJobs(request, timeout=self.timeout)

            if not response.response.success:
                if response.response.error_code == "INVALID_API_KEY":
                    raise AuthenticationError("API Key无效")
                raise DeSAMError(response.response.message)

            return {r.job_id: r.success for r in response.results}

        except grpc.RpcError as e:
            raise DeSAMConnectionError(f"gRPC调用失败: {e}")

    def get_logs(
        self,
        job_id: str,
        from_line: int = 0,
        max_lines: int = 1000,
    ) -> str:
        """获取作业日志

        Args:
            job_id: 作业ID
            from_line: 从第几行开始（默认0）
            max_lines: 最大行数（默认1000）

        Returns:
            str: 日志内容

        Raises:
            AuthenticationError: API Key无效
            JobNotFoundError: 作业不存在
        """
        request = client_pb2.GetJobLogsRequest(
            api_key=self.api_key,
            job_id=job_id,
            from_line=from_line,
            max_lines=max_lines,
        )

        try:
            response = self._stub.GetJobLogs(request, timeout=self.timeout)

            if not response.response.success:
                if response.response.error_code == "INVALID_API_KEY":
                    raise AuthenticationError("API Key无效")
                if response.response.error_code == "JOB_NOT_FOUND":
                    raise JobNotFoundError(f"作业不存在: {job_id}")
                raise DeSAMError(response.response.message)

            return response.log_content

        except grpc.RpcError as e:
            raise DeSAMConnectionError(f"gRPC调用失败: {e}")

    def close(self):
        """关闭连接"""
        if self._channel:
            self._channel.close()
            self._channel = None
            self._stub = None

    def __enter__(self):
        """上下文管理器入口"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.close()
        return False
