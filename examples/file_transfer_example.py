#!/usr/bin/env python3
"""DeSAM文件传输示例

演示如何使用DeSAM客户端进行文件上传和作业提交
"""

import os
import tempfile
from pathlib import Path


def main():
    """主函数"""
    print("=" * 60)
    print("DeSAM文件传输示例")
    print("=" * 60)

    # 步骤1: 创建临时文件用于演示
    print("\n📝 创建示例文件...")
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        # 创建数据集文件
        data_file = tmpdir / 'dataset.txt'
        with open(data_file, 'w') as f:
            for i in range(100):
                f.write(f'data line {i}\n')
        print(f"  ✓ 创建数据文件: {data_file}")

        # 创建配置文件
        config_file = tmpdir / 'config.json'
        import json
        config = {
            'learning_rate': 0.01,
            'batch_size': 32,
            'epochs': 10
        }
        with open(config_file, 'w') as f:
            json.dump(config, f, indent=2)
        print(f"  ✓ 创建配置文件: {config_file}")

        # 创建模型目录
        model_dir = tmpdir / 'models'
        model_dir.mkdir()
        (model_dir / 'model1.pth').write_text('model weights 1')
        (model_dir / 'model2.pth').write_text('model weights 2')
        print(f"  ✓ 创建模型目录: {model_dir}")

        # 步骤2: 定义文件映射
        print("\n📦 准备数据依赖...")
        file_mappings = [
            (str(data_file), 'A/dataset.txt'),      # 文件
            (str(config_file), 'A/config.json'),    # 文件
            (str(model_dir), 'A/models/'),          # 目录（自动压缩）
        ]

        for local_path, mount_path in file_mappings:
            size = Path(local_path).stat().st_size
            print(f"  - {mount_path}: {size} bytes")

        # 步骤3: 展示API使用方式
        print("\n" + "=" * 60)
        print("API使用方式")
        print("=" * 60)

        print("\n1. 创建客户端:")
        print("""
from desam_client import DeSAMClient

client = DeSAMClient(
    host='localhost',
    port=50051,
    api_key='your-api-key'
)
        """)

        print("\n2. 查询配额:")
        print("""
quota = client.files.check_quota()
print(f"可用配额: {quota.available_quota / 1024 / 1024:.2f} MB")
print(f"已用配额: {quota.used_quota / 1024 / 1024:.2f} MB")
        """)

        print("\n3. 上传单个文件:")
        print("""
def progress_callback(uploaded, total):
    percent = uploaded / total * 100
    print(f'进度: {percent:.1f}%')

file_info = client.files.upload_file(
    '/path/to/data.txt',
    progress_callback=progress_callback
)
print(f"文件ID: {file_info.file_hash}")
        """)

        print("\n4. 批量上传:")
        print("""
file_infos = client.files.upload_files([
    '/path/to/data.txt',
    '/path/to/config.json'
])
print(f"成功上传 {len(file_infos)} 个文件")
        """)

        print("\n5. 提交带数据依赖的作业:")
        print("""
job_id = client.files.submit_job_with_files(
    name='训练任务',
    command='python train.py',
    cpu=4,
    memory_mb=8192,
    file_mappings=[
        ('/path/to/data.txt', 'A/data.txt'),
        ('/path/to/config.json', 'A/config.json'),
        ('/path/to/models/', 'A/models/'),  # 目录自动压缩
    ]
)
print(f"作业已提交: {job_id}")
        """)

        # 步骤4: 展示完整示例代码
        print("\n" + "=" * 60)
        print("完整示例代码")
        print("=" * 60)

        example_code = """
from desam_client import DeSAMClient

# 初始化客户端
client = DeSAMClient(
    host='101.201.28.217',
    port=50051,
    api_key='sk-your-api-key'
)

try:
    # 检查配额
    quota = client.files.check_quota()
    print(f"可用配额: {quota.available_quota / 1024 / 1024:.2f} MB")

    # 定义文件映射 (local_path, mount_path)
    file_mappings = [
        ('/path/to/data.zip', 'A/data.zip'),
        ('/path/to/config.json', 'A/config.json'),
        ('/path/to/dataset/', 'A/dataset/'),  # 目录自动压缩
    ]

    # 提交作业（自动处理文件上传）
    job_id = client.files.submit_job_with_files(
        name='训练任务',
        command='python train.py',
        cpu=8,
        memory_mb=16384,
        gpu=1,
        file_mappings=file_mappings,
        labels={'env': 'production'},
        description='模型训练任务'
    )

    print(f"✓ 作业已提交: {job_id}")

    # 监控作业状态
    status = client.get_status(job_id)
    print(f"作业状态: {status}")

finally:
    client.close()
        """

        print(example_code)

        # 步骤5: 展示数据模型
        print("\n" + "=" * 60)
        print("数据模型")
        print("=" * 60)

        print("""
FileInfo:
  - file_hash: 文件哈希值
  - file_size: 文件大小(字节)
  - file_name: 原始文件名
  - upload_time: 上传时间

DataDependency:
  - local_path: 本地路径
  - mount_path: 挂载路径
  - file_hash: 文件哈希
  - file_size: 文件大小
  - category: A/B/C分类
    * A_CLASS: 新文件，需上传且占用配额
    * B_CLASS: 已存在但未引用，需引用且占用配额
    * C_CLASS: 已存在且已引用，不占用配额

FileTreeNode:
  - path: 文件路径
  - file_hash: 文件哈希（叶子节点）
  - is_file: 是否为文件
  - children: 子节点列表

QuotaInfo:
  - total_quota: 总配额(字节)
  - used_quota: 已用配额(字节)
  - available_quota: 可用配额(字节)
        """)

        # 步骤6: 展示文件结构
        print("\n" + "=" * 60)
        print("作业执行时的文件结构")
        print("=" * 60)

        print("""
工作目录结构:
R/
├── A/
│   ├── B.txt              # /path/to/data.txt 的内容
│   ├── config.json        # /path/to/config.json 的内容
│   ├── dataset/           # /path/to/dataset/ 的内容(解压自ZIP)
│   │   ├── file1.txt
│   │   └── file2.txt
│   └── models/            # /path/to/models/ 的内容(解压自ZIP)
│       ├── model1.pth
│       └── model2.pth
└── train.py               # 作业脚本

挂载说明:
- A/B.txt - 单个文件直接挂载
- A/dataset/ - 目录自动解压到此路径
- A/models/ - 目录自动解压到此路径
        """)

        # 步骤7: 错误处理
        print("\n" + "=" * 60)
        print("错误处理")
        print("=" * 60)

        print("""
from desam_client import DeSAMClient
from desam_client.file_transfer import (
    FileTransferError,
    QuotaExceededError,
)

try:
    job_id = client.files.submit_job_with_files(...)
except QuotaExceededError as e:
    print(f"存储配额不足: {e}")
    print("请清理一些文件或联系管理员增加配额")
except FileTransferError as e:
    print(f"文件传输失败: {e}")
except FileNotFoundError as e:
    print(f"文件不存在: {e}")
        """)

        print("\n" + "=" * 60)
        print("示例完成")
        print("=" * 60)


if __name__ == '__main__':
    main()
