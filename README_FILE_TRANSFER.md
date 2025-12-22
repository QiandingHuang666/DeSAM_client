# DeSAM Client 文件传输功能

DeSAM客户端现在支持完整的文件传输功能，包括文件上传、目录压缩、依赖验证和作业提交。

## 功能特性

### ✅ 核心功能
- **配额检查**: 查询API Key的存储配额使用情况
- **依赖验证**: 验证数据依赖（A/B/C分类）
- **文件上传**: 支持大文件分块上传（8MB块大小）
- **目录压缩**: 自动将目录压缩为ZIP再上传
- **文件树**: 构建文件树结构用于作业挂载
- **简化API**: 一行代码完成文件上传+作业提交

### 📊 依赖分类
- **A类依赖**: 调度器上没有的文件（需上传且占用配额）
- **B类依赖**: 调度器上有但API Key缓存空间无引用的文件（需引用且占用配额）
- **C类依赖**: 调度器上已存在且已引用的文件（无需操作）

## 快速开始

### 1. 初始化客户端

```python
from desam_client import DeSAMClient

client = DeSAMClient(
    host='101.201.28.217',
    port=50051,
    api_key='sk-your-api-key'
)
```

### 2. 查询存储配额

```python
from desam_client.file_transfer import QuotaInfo

quota = client.files.check_quota()
print(f"总配额: {quota.total_quota / 1024 / 1024:.2f} MB")
print(f"已用配额: {quota.used_quota / 1024 / 1024:.2f} MB")
print(f"可用配额: {quota.available_quota / 1024 / 1024:.2f} MB")
```

### 3. 上传单个文件

```python
def progress_callback(uploaded_bytes: int, total_bytes: int):
    percent = uploaded_bytes / total_bytes * 100
    print(f'上传进度: {percent:.1f}%')

file_info = client.files.upload_file(
    '/path/to/data.txt',
    progress_callback=progress_callback
)

print(f"文件哈希: {file_info.file_hash}")
print(f"文件大小: {file_info.file_size / 1024:.2f} KB")
```

### 4. 批量上传文件

```python
file_infos = client.files.upload_files([
    '/path/to/data.zip',
    '/path/to/config.json',
    '/path/to/model.pth'
])

print(f"成功上传 {len(file_infos)} 个文件")
for info in file_infos:
    print(f"  - {info.file_name}: {info.file_hash}")
```

### 5. 提交带数据依赖的作业（推荐）

```python
job_id = client.files.submit_job_with_files(
    name='训练任务',
    command='python train.py',
    cpu=8,
    memory_mb=16384,
    gpu=1,
    file_mappings=[
        ('/path/to/data.zip', 'A/data.zip'),      # 文件
        ('/path/to/config.json', 'A/config.json'),# 文件
        ('/path/to/dataset/', 'A/dataset/'),      # 目录(自动压缩)
    ],
    labels={'env': 'production'},
    description='模型训练任务'
)

print(f"✓ 作业已提交: {job_id}")
```

## API 参考

### FileManager 类

#### check_quota() -> QuotaInfo
查询API Key的存储配额。

**返回值**:
- `QuotaInfo`: 包含总配额、已用配额、可用配额

**异常**:
- `AuthenticationError`: API Key无效
- `FileTransferError`: 查询失败

#### verify_dependencies(file_hashes: List[str], total_size: int) -> DependencySet
验证数据依赖，确定A/B/C分类。

**参数**:
- `file_hashes`: 文件哈希列表
- `total_size`: 总大小（字节）

**返回值**:
- `DependencySet`: 依赖集合，包含A/B/C类依赖

#### upload_file(file_path: str, progress_callback: Optional[Callable] = None) -> FileInfo
上传单个文件。

**参数**:
- `file_path`: 本地文件路径
- `progress_callback`: 进度回调函数(uploaded_bytes, total_bytes)

**返回值**:
- `FileInfo`: 文件信息，包含哈希、大小等

**异常**:
- `FileNotFoundError`: 文件不存在
- `QuotaExceededError`: 存储配额不足
- `FileTransferError`: 上传失败

#### upload_files(file_paths: List[str]) -> List[FileInfo]
批量上传多个文件。

**参数**:
- `file_paths`: 本地文件路径列表

**返回值**:
- `List[FileInfo]`: 文件信息列表

#### build_file_tree(file_mappings: List[Tuple[str, str]]) -> FileTreeNode
构建文件树结构。

**参数**:
- `file_mappings`: (local_path, mount_path) 列表

**返回值**:
- `FileTreeNode`: 文件树根节点

#### submit_job_with_files(**kwargs) -> str
提交带数据依赖的作业（简化API）。

**参数**:
- `name`: 作业名称
- `command`: 执行命令
- `file_mappings`: (local_path, mount_path) 列表
- `cpu`: CPU核心数
- `memory_mb`: 内存大小(MB)
- `gpu`: GPU数量
- `**kwargs`: 其他参数（env, labels, description等）

**返回值**:
- `str`: 作业ID

## 数据模型

### FileInfo
文件信息对象。

```python
@dataclass
class FileInfo:
    file_hash: str           # 文件哈希(SHA256)
    file_size: int           # 文件大小(字节)
    file_name: str           # 原始文件名
    upload_time: datetime    # 上传时间
    mount_path: Optional[str] = None  # 挂载路径
```

### DataDependency
数据依赖对象。

```python
@dataclass
class DataDependency:
    local_path: str              # 本地路径
    mount_path: str              # 挂载路径
    file_hash: str               # 文件哈希
    file_size: int               # 文件大小
    category: DependencyCategory # A/B/C分类
    is_directory: bool = False   # 是否为目录
```

### DependencySet
数据依赖集合。

```python
@dataclass
class DependencySet:
    file_hashes: Set[str]                    # 所有文件哈希
    a_class_dependencies: List[DataDependency]  # A类依赖列表
    b_class_dependencies: List[DataDependency]  # B类依赖列表
    c_class_dependencies: List[DataDependency]  # C类依赖列表

    @property
    def total_a_b_size(self) -> int:
        """A类+B类依赖总大小"""
```

### FileTreeNode
文件树节点。

```python
@dataclass
class FileTreeNode:
    path: str                       # 文件路径
    file_hash: Optional[str] = None # 文件哈希（叶子节点）
    is_file: bool = True            # 是否为文件
    children: List['FileTreeNode'] = field(default_factory=list)
```

### QuotaInfo
配额信息。

```python
@dataclass
class QuotaInfo:
    total_quota: int     # 总配额(字节)
    used_quota: int      # 已用配额(字节)
    available_quota: int # 可用配额(字节)
```

## 错误处理

### 常见异常

#### QuotaExceededError
存储配额不足。

```python
from desam_client.file_transfer import QuotaExceededError

try:
    job_id = client.files.submit_job_with_files(...)
except QuotaExceededError as e:
    print(f"存储配额不足: {e}")
    print("请清理一些文件或联系管理员增加配额")
```

#### FileTransferError
文件传输错误。

```python
from desam_client.file_transfer import FileTransferError

try:
    file_info = client.files.upload_file('/path/to/file.txt')
except FileTransferError as e:
    print(f"文件传输失败: {e}")
```

#### FileNotFoundError
文件不存在。

```python
try:
    file_info = client.files.upload_file('/nonexistent/file.txt')
except FileNotFoundError as e:
    print(f"文件不存在: {e}")
```

## 工作流程

### 标准流程

```
1. 查询配额
   client.files.check_quota()

2. 验证依赖
   client.files.verify_dependencies(file_hashes, total_size)

3. 上传文件
   client.files.upload_file('/path/to/file.txt')

4. 提交作业
   client.files.submit_job_with_files(...)
```

### 简化流程

```
直接使用简化API:
client.files.submit_job_with_files(
    name='...',
    command='...',
    file_mappings=[(local_path, mount_path), ...]
)
```

系统会自动完成：配额检查 → 依赖验证 → 文件上传 → 作业提交。

## 文件结构

### 作业执行时的目录结构

```
R/                          # 作业执行根目录
├── A/                      # 数据依赖挂载根目录
│   ├── B.txt               # 单个文件直接挂载
│   ├── config.json         # 配置文件
│   ├── dataset/            # 目录自动解压
│   │   ├── file1.txt
│   │   └── file2.txt
│   └── models/             # 模型目录
│       ├── model1.pth
│       └── model2.pth
└── train.py                # 作业脚本
```

### 挂载规则

- **文件**: 直接挂载到指定路径
- **目录**: 自动压缩为ZIP，上传后解压到指定路径

## 性能优化

### 分块上传
- 默认分块大小：8MB
- 支持进度回调
- 自动重试机制

### 目录压缩
- 自动检测目录
- 使用ZIP格式压缩
- 保持目录结构

### 并发上传
- 支持多文件并发上传
- 可配置并发数

## 最佳实践

### 1. 检查配额
在上传大文件前，先检查配额是否充足。

```python
quota = client.files.check_quota()
if quota.available_quota < required_size:
    print("配额不足，请先清理文件")
```

### 2. 使用进度回调
对于大文件，使用进度回调提升用户体验。

```python
def show_progress(uploaded, total):
    bar_length = 50
    filled = int(bar_length * uploaded / total)
    bar = '█' * filled + '-' * (bar_length - filled)
    print(f'\r进度: |{bar}| {uploaded/total*100:.1f}%', end='')

client.files.upload_file('large_file.zip', progress_callback=show_progress)
```

### 3. 合理组织文件
将相关文件放在同一目录下，便于管理和压缩。

```
project/
├── data/
│   ├── train.csv
│   └── val.csv
├── config/
│   └── config.json
└── models/
    └── model.pth
```

### 4. 错误处理
始终使用try-except处理可能出现的错误。

```python
try:
    job_id = client.files.submit_job_with_files(...)
except QuotaExceededError:
    # 处理配额不足
    pass
except FileTransferError:
    # 处理传输错误
    pass
```

## 示例代码

查看 `examples/file_transfer_example.py` 获取完整的示例代码。

## 注意事项

1. **API Key权限**: 确保API Key有足够的存储配额
2. **文件大小**: 单文件大小建议不超过10GB
3. **网络稳定性**: 上传大文件时确保网络稳定
4. **临时文件**: 目录压缩会产生临时ZIP文件，注意磁盘空间
5. **清理资源**: 使用完毕后调用 `client.close()` 关闭连接

## 技术实现

### 依赖的gRPC接口
- `QueryCacheQuota`: 查询缓存配额
- `VerifyDependencies`: 验证数据依赖
- `UploadFile`: 流式文件上传
- `SubmitJobWithArtifacts`: 提交带数据依赖的作业

### 文件校验
- 使用SHA256算法计算文件哈希
- 服务端自动验证文件完整性
- 支持断点续传

### 配额管理
- 配额单位：字节（bytes）
- A类+B类依赖占用配额
- C类依赖不占用配额

## 贡献

欢迎提交Issue和Pull Request来改进这个功能。

## 许可证

本项目使用与DeSAM相同的许可证。
