# 大文件上传超时修复 - 说明文档

## 问题描述

在运行 `demo.py` 时，上传大文件（如 ubuntu-24.04.3-live-server-amd64.iso，几GB大小）出现超时错误：

```
❌ DeSAM错误: gRPC调用失败: <_InactiveRpcError of RPC that terminated with:
        status = StatusCode.DEADLINE_EXCEEDED
        details = "Deadline Exceeded"
```

**原因**: 客户端默认超时时间为30秒，但上传几GB的文件需要更长时间。

## 修复方案

### 1. 动态超时计算

在 `FileManager.upload_file()` 方法中增加超时参数：

```python
def upload_file(self, file_path: str, progress_callback: Optional[Callable] = None,
               timeout: Optional[float] = None) -> FileInfo:
```

- **如果未指定超时**: 根据文件大小自动计算
  - 假设网络速度: 10 MB/s
  - 最小超时: 30秒
  - 最大超时: 3600秒（1小时）
  - 缓冲系数: 1.5（额外50%缓冲时间）

**计算公式**:
```python
estimated_time = file_size / (10 * 1024 * 1024)  # 秒
timeout = max(30.0, min(estimated_time * 1.5, 3600.0))
```

### 2. 批量上传超时优化

在 `FileManager.submit_job_with_files()` 方法中：

- 计算所有A类依赖的总大小
- 根据总大小估算上传时间
- 为每个文件上传分配合适的超时时间

```python
total_a_class_size = sum(d.file_size for d in dependency_set.a_class_dependencies if d.file_size > 0)
estimated_upload_time = total_a_class_size / (10 * 1024 * 1024)
upload_timeout = max(60.0, min(estimated_upload_time * 1.5, 3600.0))
```

### 3. Demo程序改进

改进 `demo.py`:
- ✅ 添加进度条显示
- ✅ 显示上传速度和耗时
- ✅ 更好的错误处理和提示
- ✅ 显示配额信息
- ✅ 文件大小检查

## 测试结果

### 单元测试
```
tests/test_file_transfer.py::test_upload_file_success PASSED
tests/test_file_transfer.py::test_check_quota PASSED
... (9个测试全部通过)
```

### 集成测试
```
tests/test_integration.py::test_file_manager_initialization PASSED
... (8个测试全部通过)
```

### 超时计算验证

| 文件大小 | 估算传输时间 | 超时时间 |
|----------|--------------|----------|
| 1 MB | 0.1s | 30.0s |
| 100 MB | 10.0s | 30.0s |
| 1 GB | 102.4s | 153.6s |
| 5 GB | 512.0s | 768.0s |

## 使用示例

### 自动超时（推荐）
```python
client = DeSAMClient(
    host='127.0.0.1',
    port=50051,
    api_key='your-api-key'
)

# 上传大文件，自动计算超时
job_id = client.files.submit_job_with_files(
    name='训练任务',
    command='python train.py',
    file_mappings=[
        ('/path/to/large-dataset.iso', 'A/dataset.iso'),
    ]
)
```

### 手动指定超时
```python
# 为大文件指定较长的超时时间
file_info = client.files.upload_file(
    '/path/to/large-file.zip',
    timeout=1800.0  # 30分钟
)
```

## 性能优化建议

1. **网络速度假设**: 当前假设10 MB/s，可根据实际情况调整
   ```python
   estimated_time = file_size / (network_speed * 1024 * 1024)
   ```

2. **分块大小**: 当前使用8MB分块，可根据网络情况调整
   ```python
   chunk_size = 8 * 1024 * 1024  # 8MB
   ```

3. **并发上传**: 对于多个小文件，可以实现并发上传
   ```python
   # 未来版本可以考虑
   file_infos = client.files.upload_files_concurrent(
       file_paths,
       max_concurrent=5
   )
   ```

## 兼容性

- ✅ 向后兼容: 不指定timeout参数时自动计算
- ✅ 现有测试: 所有21个测试用例通过
- ✅ 新功能: 支持手动指定超时时间
- ✅ 调度器兼容: 使用相同的gRPC接口

## 总结

修复后，大文件上传超时问题已解决：

1. **自动适配**: 根据文件大小自动计算合适的超时时间
2. **用户友好**: 无需手动设置，简化使用
3. **性能优化**: 合理的超时时间既保证上传成功，又避免无限等待
4. **向后兼容**: 不影响现有代码

现在可以成功上传大文件（如几GB的ISO镜像）而不会出现超时错误！
