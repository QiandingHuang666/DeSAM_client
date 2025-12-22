"""文件传输管理器"""

import os
from typing import Callable, Dict, List, Optional, Tuple

import grpc

from .._grpc import client_pb2, client_pb2_grpc
from ..exceptions import DeSAMError
from .models import (
    DataDependency,
    DependencyCategory,
    DependencySet,
    FileInfo,
    FileTreeNode,
    QuotaInfo,
)
from .checksum import calculate_file_hash, calculate_directory_hash, get_file_size, get_directory_size
from .compression import compress_directory_to_zip


class FileTransferError(DeSAMError):
    """文件传输错误"""
    pass


class QuotaExceededError(FileTransferError):
    """存储配额不足"""
    pass


class FileManager:
    """文件管理器"""

    def __init__(self, client: 'DeSAMClient'):
        """初始化FileManager

        Args:
            client: DeSAMClient实例
        """
        self._client = client
        self._compressed_files = {}  # 缓存压缩的目录文件

    def _get_stub(self) -> client_pb2_grpc.ClientServiceStub:
        """获取gRPC Stub"""
        return self._client._stub

    def check_quota(self) -> QuotaInfo:
        """查询存储配额

        Returns:
            QuotaInfo: 配额信息

        Raises:
            AuthenticationError: API Key无效
            FileTransferError: 查询失败
        """
        request = client_pb2.QueryCacheQuotaRequest(
            api_key=self._client.api_key
        )

        try:
            response = self._get_stub().QueryCacheQuota(request, timeout=self._client.timeout)

            if not response.response.success:
                raise FileTransferError(f"查询配额失败: {response.response.message}")

            return QuotaInfo(
                total_quota=response.total_quota,
                used_quota=response.used_quota,
                available_quota=response.available_quota,
            )

        except grpc.RpcError as e:
            raise FileTransferError(f"gRPC调用失败: {e}")

    def verify_dependencies(self, file_hashes: List[str], total_size: int) -> DependencySet:
        """验证数据依赖

        Args:
            file_hashes: 文件哈希列表
            total_size: 总大小

        Returns:
            DependencySet: 依赖集合

        Raises:
            FileTransferError: 验证失败
        """
        request = client_pb2.VerifyDependenciesRequest(
            api_key=self._client.api_key,
            file_hashes=file_hashes,
            total_size=total_size,
        )

        try:
            response = self._get_stub().VerifyDependencies(request, timeout=self._client.timeout)

            if not response.response.success:
                raise FileTransferError(f"验证依赖失败: {response.response.message}")

            # 创建依赖集合
            dependency_set = DependencySet()
            dependency_set.file_hashes.update(file_hashes)

            # 根据missing_hashes和existing_hashes分类依赖
            for file_hash in response.missing_hashes:
                dependency = DataDependency(
                    local_path="",  # 未知本地路径
                    mount_path="",
                    file_hash=file_hash,
                    file_size=0,  # 暂时设为0，在submit_job_with_files中更新
                    category=DependencyCategory.A_CLASS,
                )
                dependency_set.a_class_dependencies.append(dependency)

            for file_hash in response.existing_hashes:
                dependency = DataDependency(
                    local_path="",
                    mount_path="",
                    file_hash=file_hash,
                    file_size=0,
                    category=DependencyCategory.B_CLASS,  # 假设都是B类
                )
                dependency_set.b_class_dependencies.append(dependency)

            return dependency_set

        except grpc.RpcError as e:
            raise FileTransferError(f"gRPC调用失败: {e}")

    def upload_file(self, file_path: str, progress_callback: Optional[Callable] = None,
                   timeout: Optional[float] = None) -> FileInfo:
        """上传单个文件

        Args:
            file_path: 本地文件路径
            progress_callback: 进度回调函数(uploaded_bytes, total_bytes)
            timeout: 上传超时时间（秒），如果未指定则根据文件大小自动计算

        Returns:
            FileInfo: 文件信息

        Raises:
            FileNotFoundError: 文件不存在
            FileTransferError: 上传失败
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"文件不存在: {file_path}")

        # 计算文件哈希和大小
        file_hash = calculate_file_hash(file_path)
        file_size = get_file_size(file_path)
        file_name = os.path.basename(file_path)

        # 如果没有指定超时时间，根据文件大小自动计算
        # 假设网络速度为 10 MB/s，加上一些缓冲时间
        if timeout is None:
            # 最小超时30秒，最大超时3600秒（1小时）
            estimated_time = file_size / (10 * 1024 * 1024)  # 秒
            timeout = max(30.0, min(estimated_time * 1.5, 3600.0))

        # 分块上传
        chunk_size = 8 * 1024 * 1024  # 8MB

        def generate_chunks():
            with open(file_path, 'rb') as f:
                chunk_id = 0
                while True:
                    chunk_data = f.read(chunk_size)
                    if not chunk_data:
                        break

                    is_last = len(chunk_data) < chunk_size

                    yield client_pb2.UploadFileRequest(
                        api_key=self._client.api_key,
                        file_hash=file_hash,
                        file_size=file_size,
                        file_name=file_name,
                        content=chunk_data,
                        is_last_chunk=is_last,
                        chunk_id=str(chunk_id)
                    )

                    # 进度回调
                    if progress_callback:
                        uploaded = chunk_id * chunk_size + len(chunk_data)
                        progress_callback(uploaded, file_size)

                    chunk_id += 1

        try:
            response = self._get_stub().UploadFile(generate_chunks(), timeout=timeout)

            if not response.response.success:
                raise FileTransferError(f"上传失败: {response.response.message}")

            return FileInfo(
                file_hash=response.file_hash,
                file_size=file_size,
                file_name=file_name,
                upload_time=None,  # 响应中没有时间信息
            )

        except grpc.RpcError as e:
            raise FileTransferError(f"gRPC调用失败: {e}")

    def upload_files(self, file_paths: List[str]) -> List[FileInfo]:
        """批量上传文件

        Args:
            file_paths: 本地文件路径列表

        Returns:
            List[FileInfo]: 文件信息列表

        Raises:
            FileTransferError: 上传失败
        """
        results = []
        for file_path in file_paths:
            try:
                file_info = self.upload_file(file_path)
                results.append(file_info)
            except Exception as e:
                raise FileTransferError(f"上传文件失败 {file_path}: {e}")

        return results

    def build_file_tree(self, file_mappings: List[Tuple[str, str]]) -> FileTreeNode:
        """构建文件树

        Args:
            file_mappings: (local_path, mount_path) 列表

        Returns:
            FileTreeNode: 文件树根节点
        """
        # 创建根节点
        root = FileTreeNode(path="", is_file=False)

        for local_path, mount_path in file_mappings:
            # 计算文件哈希（使用缓存加速）
            if os.path.isfile(local_path):
                file_hash = calculate_file_hash(local_path, use_cache=True)
                is_dir = False
            else:
                # 目录需要先压缩
                zip_path = compress_directory_to_zip(local_path)
                file_hash = calculate_file_hash(zip_path, use_cache=True)
                is_dir = True
                # 缓存压缩文件路径
                self._compressed_files[mount_path] = zip_path

            # 构建路径
            path_parts = mount_path.strip('/').split('/')
            self._add_to_tree(root, path_parts, file_hash, is_dir)

        return root

    def _add_to_tree(self, node: FileTreeNode, path_parts: List[str],
                    file_hash: str, is_dir: bool) -> None:
        """将文件添加到树中"""
        if len(path_parts) == 1:
            # 叶子节点
            leaf = FileTreeNode(
                path=path_parts[0],
                file_hash=file_hash if not is_dir else None,
                is_file=not is_dir
            )
            node.children.append(leaf)
        else:
            # 目录节点
            dir_name = path_parts[0]
            # 查找或创建目录节点
            dir_node = None
            for child in node.children:
                if child.path == dir_name and not child.is_file:
                    dir_node = child
                    break

            if not dir_node:
                dir_node = FileTreeNode(
                    path=dir_name,
                    is_file=False
                )
                node.children.append(dir_node)

            # 递归处理剩余路径
            self._add_to_tree(dir_node, path_parts[1:], file_hash, is_dir)

    def _build_file_tree_proto(self, file_mappings: List[Tuple[str, str]]) -> 'client_pb2.FileTreeNode':
        """构建protobuf格式的文件树

        Args:
            file_mappings: (local_path, mount_path) 列表

        Returns:
            FileTreeNode protobuf消息
        """
        # 创建根节点
        root = client_pb2.FileTreeNode()
        root.path = ""
        root.is_file = False

        for local_path, mount_path in file_mappings:
            # 计算文件哈希（使用缓存加速）
            if os.path.isfile(local_path):
                file_hash = calculate_file_hash(local_path, use_cache=True)
                is_dir = False
            else:
                # 目录需要先压缩
                zip_path = compress_directory_to_zip(local_path)
                file_hash = calculate_file_hash(zip_path, use_cache=True)
                is_dir = True
                # 缓存压缩文件路径
                self._compressed_files[mount_path] = zip_path

            # 构建路径
            path_parts = mount_path.strip('/').split('/')
            self._add_to_tree_proto(root, path_parts, file_hash, is_dir)

        return root

    def _add_to_tree_proto(self, node: 'client_pb2.FileTreeNode', path_parts: List[str],
                          file_hash: str, is_dir: bool) -> None:
        """将文件添加到protobuf树中"""
        if len(path_parts) == 1:
            # 叶子节点
            leaf = node.children.add()
            leaf.path = path_parts[0]
            leaf.is_file = not is_dir
            if not is_dir:
                leaf.file_hash = file_hash
        else:
            # 目录节点
            dir_name = path_parts[0]
            # 查找或创建目录节点
            dir_node = None
            for child in node.children:
                if child.path == dir_name and not child.is_file:
                    dir_node = child
                    break

            if not dir_node:
                dir_node = node.children.add()
                dir_node.path = dir_name
                dir_node.is_file = False

            # 递归处理剩余路径
            self._add_to_tree_proto(dir_node, path_parts[1:], file_hash, is_dir)

    def submit_job_with_files(
        self,
        name: str,
        command: str,
        file_mappings: List[Tuple[str, str]],
        cpu: int = 1,
        memory_mb: int = 1024,
        gpu: int = 0,
        disk_mb: int = 0,
        **kwargs
    ) -> str:
        """提交带数据依赖的作业（简化API）

        Args:
            name: 作业名称
            command: 执行命令
            file_mappings: (local_path, mount_path) 列表
            cpu: CPU核心数
            memory_mb: 内存大小(MB)
            gpu: GPU数量
            disk_mb: 磁盘空间(MB)
            **kwargs: 其他参数

        Returns:
            str: 作业ID

        Raises:
            FileTransferError: 提交失败
        """
        # 步骤1: 计算所有文件的哈希
        file_hashes = []
        total_size = 0
        hash_to_path = {}  # 哈希到文件路径的映射

        for local_path, mount_path in file_mappings:
            if os.path.isfile(local_path):
                file_hash = calculate_file_hash(local_path, use_cache=True)
                file_size = get_file_size(local_path)
                hash_to_path[file_hash] = local_path
            else:
                # 目录压缩后再计算
                zip_path = compress_directory_to_zip(local_path)
                file_hash = calculate_file_hash(zip_path, use_cache=True)
                file_size = get_file_size(zip_path)
                hash_to_path[file_hash] = zip_path
                self._compressed_files[mount_path] = zip_path

            file_hashes.append(file_hash)
            total_size += file_size

        # 步骤2: 验证依赖
        dependency_set = self.verify_dependencies(file_hashes, total_size)

        # 更新依赖的文件大小
        for dependency in dependency_set.a_class_dependencies:
            if dependency.file_hash in hash_to_path:
                file_path = hash_to_path[dependency.file_hash]
                if os.path.isfile(file_path):
                    dependency.file_size = get_file_size(file_path)
                    dependency.local_path = file_path
                elif os.path.isdir(file_path):
                    # 对于目录，使用压缩后的大小
                    zip_path = self._compressed_files.get(
                        [k for k, v in hash_to_path.items() if v == file_path][0] if file_path in hash_to_path.values() else ""
                    )
                    if zip_path and os.path.exists(zip_path):
                        dependency.file_size = get_file_size(zip_path)
                        dependency.local_path = zip_path

        # 步骤3: 检查配额
        quota = self.check_quota()
        if dependency_set.total_a_b_size > quota.available_quota:
            raise QuotaExceededError(
                f"A类+B类依赖总大小 {dependency_set.total_a_b_size} 超过可用配额 {quota.available_quota}"
            )

        # 步骤4: 上传A类依赖
        if dependency_set.a_class_dependencies:
            # 计算所有A类依赖的总大小，用于估算超时时间
            total_a_class_size = sum(d.file_size for d in dependency_set.a_class_dependencies if d.file_size > 0)

            # 根据总大小计算超时时间（假设网络速度10 MB/s）
            estimated_upload_time = total_a_class_size / (10 * 1024 * 1024)  # 秒
            upload_timeout = max(60.0, min(estimated_upload_time * 1.5, 3600.0))  # 最小60秒，最大1小时

            # 上传每个A类依赖
            for dependency in dependency_set.a_class_dependencies:
                local_path = hash_to_path.get(dependency.file_hash)
                if local_path and os.path.exists(local_path):
                    # 上传文件，传递超时时间
                    self.upload_file(local_path, timeout=upload_timeout)
                else:
                    raise FileTransferError(f"找不到A类依赖对应的本地文件: {dependency.file_hash}")

        # 步骤5: 构建文件树并转换为protobuf格式
        file_tree_proto = self._build_file_tree_proto(file_mappings)

        # 步骤6: 提交作业
        request = client_pb2.SubmitJobWithArtifactsRequest()
        request.api_key = self._client.api_key
        request.user_id = kwargs.get('user_id', 'default_user')
        request.name = name
        request.command = command
        request.working_dir = kwargs.get('working_dir', '')
        request.resources.cpu_cores = cpu
        request.resources.memory_mb = memory_mb
        request.resources.gpu_count = gpu
        request.resources.disk_mb = disk_mb
        request.metadata.update(kwargs.get('metadata', {}))
        request.env.update(kwargs.get('env', {}))
        request.timeout = kwargs.get('timeout', 0)
        request.retries = kwargs.get('retries', 0)
        request.labels.update(kwargs.get('labels', {}))
        request.description = kwargs.get('description', '')
        request.file_hashes.extend(file_hashes)
        request.file_tree.CopyFrom(file_tree_proto)

        try:
            response = self._get_stub().SubmitJobWithArtifacts(request, timeout=self._client.timeout)

            if not response.response.success:
                raise FileTransferError(f"提交作业失败: {response.response.message}")

            return response.job_id

        except grpc.RpcError as e:
            raise FileTransferError(f"gRPC调用失败: {e}")
