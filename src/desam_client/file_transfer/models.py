"""文件传输相关数据模型"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple


class DependencyCategory(Enum):
    """依赖分类"""
    A_CLASS = "A"  # 调度器上没有，需上传且占用配额
    B_CLASS = "B"  # 调度器上有，但API Key缓存空间无引用，需引用且占用配额
    C_CLASS = "C"  # 调度器上有，API Key缓存空间已引用，不占用配额


@dataclass
class FileInfo:
    """文件信息"""
    file_hash: str  # 文件哈希(SHA256)
    file_size: int  # 文件大小(字节)
    file_name: str  # 原始文件名
    upload_time: datetime  # 上传时间
    mount_path: Optional[str] = None  # 挂载路径


@dataclass
class DataDependency:
    """数据依赖"""
    local_path: str  # 本地路径
    mount_path: str  # 挂载路径
    file_hash: str  # 文件哈希
    file_size: int  # 文件大小
    category: DependencyCategory  # A/B/C分类
    is_directory: bool = False  # 是否为目录


@dataclass
class DependencySet:
    """数据依赖集合"""
    file_hashes: Set[str] = field(default_factory=set)
    a_class_dependencies: List[DataDependency] = field(default_factory=list)
    b_class_dependencies: List[DataDependency] = field(default_factory=list)
    c_class_dependencies: List[DataDependency] = field(default_factory=list)

    @property
    def total_a_b_size(self) -> int:
        """A类+B类依赖总大小"""
        return sum(d.file_size for d in self.a_class_dependencies + self.b_class_dependencies)


@dataclass
class FileTreeNode:
    """文件树节点"""
    path: str  # 文件路径
    file_hash: Optional[str] = None  # 文件哈希（叶子节点）
    is_file: bool = True  # 是否为文件（否则为目录）
    children: List['FileTreeNode'] = field(default_factory=list)


@dataclass
class QuotaInfo:
    """配额信息"""
    total_quota: int  # 总配额(字节)
    used_quota: int  # 已用配额(字节)
    available_quota: int  # 可用配额(字节)
