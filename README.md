# DeSAM Client

DeSAM调度器的官方Python客户端库，提供简单易用的API与DeSAM调度器进行通信。

[![Python Version](https://img.shields.io/badge/python-3.8+-blue.svg)](https://python.org/downloads/)
[![gRPC](https://img.shields.io/badge/gRPC-1.60+-green.svg)](https://grpc.io/)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)

## ✨ 特性

- **完整的作业管理**: 提交、查询、取消、列表作业
- **批量操作**: 支持批量查询和取消作业
- **丰富的作业元数据**: 支持环境变量、超时、重试、标签等
- **数据依赖管理**: 管理作业的数据依赖文件
- **异步支持**: 基于gRPC的异步通信
- **错误处理**: 完整的异常体系和错误提示
- **类型安全**: 使用Python类型提示提供更好的开发体验
- **TLS支持**: 生产环境的安全通信
- **上下文管理**: 支持`with`语句的资源管理

## 📦 安装

### 使用pip安装（推荐）

```bash
pip install desam-client
```

### 从源码安装

```bash
git clone https://github.com/your-org/DeSAM.git
cd DeSAM/DeSAM_client
pip install -e .
```

### 使用uv安装（开发环境）

```bash
uv sync
```

## 🚀 快速开始

### 基本使用

```python
from desam_client import DeSAMClient

# 连接调度器（TLS证书是必需的）
client = DeSAMClient(
    host="192.168.1.100",
    port=50051,
    api_key="sk-your-api-key",
    cert_path="./server.crt"  # 必须提供TLS证书路径以确保安全连接
)
```

try:
    # 提交作业
    job_id = client.submit_job(
        name="训练任务",
        command="python train.py --model resnet50",
        cpu=8,
        memory_mb=16384,
        gpu=1,
        env={"CUDA_VISIBLE_DEVICES": "0"},
        timeout=3600,
        artifacts=["dataset.zip", "pretrained.pth"],
        labels={"project": "cv", "experiment": "baseline"}
    )
    print(f"作业已提交: {job_id}")

    # 查询状态
    status = client.get_status(job_id)
    print(f"状态: {status}")

    # 获取完整信息
    job = client.get_info(job_id)
    print(f"作业详情: {job}")

    # 取消作业
    if client.cancel(job_id):
        print("作业已取消")

finally:
    client.close()
```

### 使用上下文管理器（推荐）

```python
from desam_client import DeSAMClient

with DeSAMClient(
    host="localhost",
    port=50051,
    api_key="sk-your-api-key"
) as client:
    job_id = client.submit_job(
        name="测试作业",
        command="echo 'Hello World'",
        cpu=1,
        memory_mb=1024
    )
    print(f"作业提交成功: {job_id}")
```

## 📚 完整示例

### 深度学习训练作业

```python
from desam_client import DeSAMClient

client = DeSAMClient(
    host="localhost",
    port=50051,
    api_key="sk-admin-1234567890abcdef"
)

# 提交一个深度学习训练作业
job_id = client.submit_job(
    name="ResNet50训练",
    command="python train.py --model resnet50 --epochs 100 --lr 0.01",
    cpu=8,
    memory_mb=32768,
    gpu=2,
    working_dir="/workspace/training",
    env={
        "CUDA_VISIBLE_DEVICES": "0,1",
        "DATA_PATH": "/data/imagenet",
        "MODEL_PATH": "/models",
        "TENSORBOARD_LOG": "/logs"
    },
    timeout=7200,  # 2小时
    retries=2,      # 失败重试2次
    artifacts=[
        "dataset/imagenet/train.zip",
        "dataset/imagenet/val.zip",
        "models/resnet50-pretrained.pth",
        "configs/training_config.yaml"
    ],
    labels={
        "project": "computer-vision",
        "experiment": "resnet50-baseline",
        "dataset": "imagenet",
        "priority": "high"
    },
    description="使用ResNet50在ImageNet数据集上训练基线模型",
    metadata={
        "owner": "alice@example.com",
        "cost_center": "ML-PLATFORM"
    }
)

print(f"作业提交成功: {job_id}")
```

### 批量操作

```python
from desam_client import DeSAMClient

client = DeSAMClient(
    host="localhost",
    port=50051,
    api_key="sk-your-api-key"
)

# 提交多个作业
job_ids = []
for i in range(5):
    jid = client.submit_job(
        name=f"批量作业-{i+1}",
        command=f"python batch_process.py --batch {i}",
        cpu=2,
        memory_mb=4096
    )
    job_ids.append(jid)

# 批量查询
jobs = client.batch_get_info(job_ids)
print(f"获取到 {len(jobs)} 个作业信息")

# 批量取消
results = client.batch_cancel(job_ids)
for job_id, success in results.items():
    print(f"{job_id}: {'取消成功' if success else '取消失败'}")
```

### 监控作业状态

```python
from desam_client import DeSAMClient
import time

client = DeSAMClient(
    host="localhost",
    port=50051,
    api_key="sk-your-api-key"
)

job_id = client.submit_job(
    name="长时间作业",
    command="python long_task.py",
    cpu=4,
    memory_mb=8192
)

# 轮询查询作业状态
while True:
    status = client.get_status(job_id)
    print(f"作业状态: {status}")

    if status in ["SUCCEEDED", "FAILED", "CANCELLED"]:
        break

    time.sleep(5)  # 每5秒查询一次

# 获取最终结果
job = client.get_info(job_id)
print(f"作业完成: {job.status}")
print(f"错误信息: {job.error_message}")
```

## 📖 API 参考

### DeSAMClient 类

#### 构造函数

```python
DeSAMClient(
    host: str,              # 调度器地址（必需）
    port: int = 50051,      # 调度器端口（默认50051）
    api_key: str,           # API Key（必需）
    cert_path: str = None,  # TLS证书路径（可选）
    timeout: float = 30.0   # 请求超时时间（默认30秒）
)
```

**参数说明**:
- `host`: 调度器的IP地址或域名
- `port`: 调度器的gRPC端口（Client服务默认50051）
- `api_key`: 认证用的API Key
- `cert_path`: TLS证书文件路径（可选，生产环境建议使用）
- `timeout`: 单次gRPC调用的超时时间（秒）

#### 方法

##### submit_job() - 提交作业

```python
def submit_job(
    self,
    name: str,                          # 作业名称（必需）
    command: str,                       # 执行命令（必需）
    cpu: int = 1,                       # CPU核心数（默认1）
    memory_mb: int = 1024,              # 内存大小MB（默认1024）
    gpu: int = 0,                       # GPU数量（默认0）
    disk_mb: int = 0,                   # 磁盘空间MB（默认0）
    working_dir: Optional[str] = None,  # 工作目录（可选）
    env: Optional[Dict[str, str]] = None,       # 环境变量（可选）
    timeout: Optional[int] = None,      # 超时时间秒（可选）
    retries: int = 0,                   # 重试次数（默认0）
    artifacts: Optional[List[str]] = None,      # 数据依赖文件列表（可选）
    labels: Optional[Dict[str, str]] = None,    # 标签（可选）
    description: Optional[str] = None,  # 描述（可选）
    metadata: Optional[Dict[str, str]] = None,  # 元数据（可选）
    user_id: Optional[str] = None,      # 用户ID（可选）
) -> str:
```

**返回**: 作业ID字符串

**示例**:
```python
job_id = client.submit_job(
    name="AI训练作业",
    command="python train.py",
    cpu=8,
    memory_mb=16384,
    gpu=2,
    env={"CUDA_VISIBLE_DEVICES": "0"},
    timeout=3600,
    retries=2,
    artifacts=["dataset.zip"],
    labels={"project": "cv"},
    description="深度学习训练"
)
```

##### get_status() - 获取作业状态

```python
def get_status(self, job_id: str) -> str:
```

**参数**:
- `job_id`: 作业ID

**返回**: 作业状态字符串（"QUEUED"/"PREPARING"/"RUNNING"/"SUCCEEDED"/"FAILED"/"CANCELLED"/"TIMEOUT"）

**示例**:
```python
status = client.get_status("job-123456")
print(f"作业状态: {status}")  # 输出: QUEUED
```

##### get_info() - 获取作业完整信息

```python
def get_info(self, job_id: str) -> Job:
```

**参数**:
- `job_id`: 作业ID

**返回**: Job对象，包含完整的作业信息

**示例**:
```python
job = client.get_info("job-123456")
print(f"作业名称: {job.name}")
print(f"执行命令: {job.command}")
print(f"资源需求: CPU {job.resources.cpu}核, 内存 {job.resources.memory_mb}MB")
print(f"环境变量: {job.env}")
print(f"标签: {job.labels}")
print(f"提交时间: {job.submit_time}")
```

##### list_jobs() - 列出作业

```python
def list_jobs(
    self,
    user_id: Optional[str] = None,  # 用户ID过滤（可选）
    status: Optional[str] = None,    # 状态过滤（可选）
    limit: int = 100,                # 返回数量限制（默认100）
    offset: int = 0                  # 偏移量（分页用）
) -> List[Job]:
```

**参数**:
- `user_id`: 按用户ID过滤（可选）
- `status`: 按状态过滤（可选）
- `limit`: 返回数量限制（默认100）
- `offset`: 偏移量（分页用）

**返回**: Job对象列表

**示例**:
```python
# 获取所有作业
all_jobs = client.list_jobs()

# 获取特定用户的作业
user_jobs = client.list_jobs(user_id="alice")

# 获取正在运行的作业
running_jobs = client.list_jobs(status="RUNNING", limit=10)

# 分页查询
page1 = client.list_jobs(offset=0, limit=20)
page2 = client.list_jobs(offset=20, limit=20)
```

##### cancel() - 取消作业

```python
def cancel(self, job_id: str) -> bool:
```

**参数**:
- `job_id`: 作业ID

**返回**: 是否成功取消

**示例**:
```python
success = client.cancel("job-123456")
if success:
    print("作业取消成功")
else:
    print("作业取消失败")
```

##### batch_get_info() - 批量获取作业信息

```python
def batch_get_info(self, job_ids: List[str]) -> List[Job]:
```

**参数**:
- `job_ids`: 作业ID列表

**返回**: Job对象列表

**示例**:
```python
job_ids = ["job-1", "job-2", "job-3"]
jobs = client.batch_get_info(job_ids)
for job in jobs:
    print(f"{job.job_id}: {job.name}")
```

##### batch_cancel() - 批量取消作业

```python
def batch_cancel(self, job_ids: List[str]) -> Dict[str, bool]:
```

**参数**:
- `job_ids`: 作业ID列表

**返回**: 字典 {job_id: success}，表示各作业的取消结果

**示例**:
```python
job_ids = ["job-1", "job-2", "job-3"]
results = client.batch_cancel(job_ids)
for job_id, success in results.items():
    print(f"{job_id}: {'取消成功' if success else '取消失败'}")
```

##### get_logs() - 获取作业日志

```python
def get_logs(
    self,
    job_id: str,               # 作业ID
    from_line: int = 0,        # 从第几行开始（默认0）
    max_lines: int = 1000      # 最大行数（默认1000）
) -> str:
```

**参数**:
- `job_id`: 作业ID
- `from_line`: 从第几行开始（默认0）
- `max_lines`: 最大行数（默认1000）

**返回**: 日志内容字符串

**示例**:
```python
logs = client.get_logs("job-123456")
print(logs)

# 获取最近100行
recent_logs = client.get_logs("job-123456", from_line=100, max_lines=100)
print(recent_logs)
```

##### close() - 关闭连接

```python
def close(self) -> None:
```

关闭与调度器的gRPC连接。

**示例**:
```python
client.close()
# 或使用上下文管理器自动关闭
with DeSAMClient(...) as client:
    # 作业操作
    pass
```

## 📊 数据模型

### Job 类

作业信息对象，包含以下字段：

| 字段 | 类型 | 说明 |
|------|------|------|
| `job_id` | str | 作业ID |
| `user_id` | str | 用户ID |
| `name` | str | 作业名称 |
| `command` | str | 执行命令 |
| `status` | str | 作业状态 |
| `resources` | Resource | 资源需求 |
| `working_dir` | Optional[str] | 工作目录 |
| `env` | Optional[Dict[str, str]] | 环境变量 |
| `timeout` | Optional[int] | 超时时间（秒） |
| `retries` | int | 重试次数 |
| `artifacts` | Optional[List[str]] | 数据依赖文件列表 |
| `labels` | Optional[Dict[str, str]] | 标签 |
| `description` | Optional[str] | 描述 |
| `metadata` | Optional[Dict[str, str]] | 元数据 |
| `submit_time` | Optional[datetime] | 提交时间 |
| `start_time` | Optional[datetime] | 开始时间 |
| `finish_time` | Optional[datetime] | 完成时间 |
| `error_message` | Optional[str] | 错误信息 |
| `executor_id` | Optional[str] | 执行器ID |

### Resource 类

资源需求对象，包含以下字段：

| 字段 | 类型 | 说明 |
|------|------|------|
| `cpu` | int | CPU核心数 |
| `memory_mb` | int | 内存大小（MB） |
| `gpu` | int | GPU数量 |
| `disk_mb` | int | 磁盘空间（MB） |

### 作业状态

作业状态的可能值：

| 状态 | 说明 |
|------|------|
| `UNKNOWN` | 未知状态 |
| `QUEUED` | 等待队列 |
| `PREPARING` | 准备中 |
| `RUNNING` | 执行中 |
| `SUCCEEDED` | 成功完成 |
| `FAILED` | 执行失败 |
| `CANCELLED` | 已取消 |
| `TIMEOUT` | 超时 |

## ❌ 异常类

| 异常类 | 描述 | 触发条件 |
|--------|------|----------|
| `DeSAMError` | 基础异常类 | 所有DeSAM相关错误的基类 |
| `AuthenticationError` | 认证失败 | API Key无效或过期 |
| `JobNotFoundError` | 作业不存在 | 查询不存在的作业 |
| `DeSAMConnectionError` | 连接失败 | 无法连接到调度器 |
| `SubmitError` | 提交失败 | 作业提交时发生错误 |

**示例**:
```python
from desam_client import (
    DeSAMClient,
    AuthenticationError,
    JobNotFoundError,
    DeSAMError
)

try:
    job_id = client.submit_job(...)
except AuthenticationError:
    print("API Key无效，请检查")
except JobNotFoundError as e:
    print(f"作业不存在: {e}")
except DeSAMError as e:
    print(f"DeSAM错误: {e}")
```

## 🔐 认证和TLS

### API Key 认证

所有API调用都需要有效的API Key：

```python
client = DeSAMClient(
    host="localhost",
    port=50051,
    api_key="sk-your-api-key"
)
```

获取API Key请联系调度器管理员。

### TLS 安全连接（生产环境）

生产环境建议使用TLS加密：

```python
client = DeSAMClient(
    host="scheduler.example.com",
    port=50051,
    api_key="sk-your-api-key",
    cert_path="./server.crt"  # 服务器证书路径
)
```

证书文件应从调度器管理员获取。

## 🛠️ 最佳实践

### 1. 使用上下文管理器

始终使用`with`语句确保资源正确释放：

```python
# 推荐
with DeSAMClient(...) as client:
    job_id = client.submit_job(...)
    # 作业操作

# 不推荐
client = DeSAMClient(...)
# ... 使用 ...
client.close()  # 可能忘记调用
```

### 2. 错误处理

始终捕获和处理异常：

```python
from desam_client import DeSAMClient, DeSAMError

try:
    job_id = client.submit_job(...)
except DeSAMError as e:
    print(f"提交失败: {e}")
    # 处理错误
```

### 3. 资源请求

合理请求资源，避免浪费：

```python
# 根据实际需要请求资源
job_id = client.submit_job(
    name="训练作业",
    command="python train.py",
    cpu=8,          # 需要8核CPU
    memory_mb=16384,  # 需要16GB内存
    gpu=2,          # 需要2块GPU
)
```

### 4. 超时设置

根据作业预期执行时间设置超时：

```python
# 短作业
job_id = client.submit_job(
    name="快速任务",
    command="echo hello",
    timeout=300  # 5分钟
)

# 长作业
job_id = client.submit_job(
    name="长时间训练",
    command="python train.py --epochs 1000",
    timeout=86400  # 24小时
)
```

### 5. 使用标签管理作业

使用标签组织和分类作业：

```python
job_id = client.submit_job(
    name="实验",
    command="python experiment.py",
    labels={
        "project": "cv",
        "experiment": "resnet50",
        "version": "v1.0",
        "owner": "alice"
    }
)

# 按标签查询
all_jobs = client.list_jobs()
cv_jobs = [j for j in all_jobs if j.labels and j.labels.get("project") == "cv"]
```

### 6. 重试机制

为关键作业设置重试：

```python
job_id = client.submit_job(
    name="重要作业",
    command="python critical_task.py",
    retries=3  # 失败时重试3次
)
```

## 🔍 故障排除

### 连接失败

**错误**: `DeSAMConnectionError: 连接调度器失败`

**解决方案**:
1. 检查调度器地址和端口是否正确
2. 检查网络连接
3. 检查防火墙设置
4. 验证调度器是否正常运行

### 认证失败

**错误**: `AuthenticationError: API Key无效`

**解决方案**:
1. 验证API Key是否正确
2. 检查API Key是否过期
3. 联系管理员获取有效的API Key

### 作业不存在

**错误**: `JobNotFoundError: 作业不存在`

**解决方案**:
1. 验证作业ID是否正确
2. 检查作业是否已被删除
3. 确认作业ID的拼写

### 资源不足

**错误**: `SubmitError: 资源不足`

**解决方案**:
1. 检查调度器可用资源
2. 减少资源请求（CPU、内存、GPU）
3. 等待其他作业完成释放资源

### 超时

**错误**: gRPC超时

**解决方案**:
1. 增加客户端超时时间
2. 检查网络延迟
3. 检查调度器负载

## 📚 更多信息

- [DeSAM调度器文档](https://github.com/your-org/DeSAM)
- [gRPC Python文档](https://grpc.io/docs/languages/python/)
- [示例代码](./demo.py)

## 📄 许可证

本项目采用 Apache 2.0 许可证。详情请参阅 [LICENSE](LICENSE) 文件。

## 🤝 贡献

欢迎提交Issue和Pull Request！

## 📞 支持

如有问题请创建 [Issue](https://github.com/your-org/DeSAM/issues)。
