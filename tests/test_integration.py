"""文件传输集成测试"""

import os
import tempfile
from pathlib import Path
from unittest.mock import Mock
import pytest

from desam_client import DeSAMClient
from desam_client.file_transfer.manager import FileTransferError, QuotaExceededError


class TestFileTransferIntegration:
    """文件传输集成测试"""

    @pytest.fixture
    def temp_files(self):
        """创建临时文件"""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            # 创建测试文件
            data_file = tmpdir / 'data.txt'
            data_file.write_text('test data\n' * 100)

            # 创建配置文件
            config_file = tmpdir / 'config.json'
            config_file.write_text('{"key": "value"}')

            # 创建测试目录
            model_dir = tmpdir / 'models'
            model_dir.mkdir()
            (model_dir / 'model1.bin').write_bytes(b'model data 1')
            (model_dir / 'model2.bin').write_bytes(b'model data 2')

            yield {
                'dir': tmpdir,
                'data_file': str(data_file),
                'config_file': str(config_file),
                'model_dir': str(model_dir),
            }

    def test_file_info_creation(self):
        """测试FileInfo创建"""
        from desam_client.file_transfer.models import FileInfo
        from datetime import datetime

        file_info = FileInfo(
            file_hash="abc123",
            file_size=1024,
            file_name="test.txt",
            upload_time=datetime.now()
        )

        assert file_info.file_hash == "abc123"
        assert file_info.file_size == 1024
        assert file_info.file_name == "test.txt"

    def test_dependency_set(self):
        """测试DependencySet"""
        from desam_client.file_transfer.models import (
            DependencySet,
            DataDependency,
            DependencyCategory,
        )

        dep_set = DependencySet()

        # 添加依赖
        dep1 = DataDependency(
            local_path="/test1",
            mount_path="A/test1",
            file_hash="hash1",
            file_size=100,
            category=DependencyCategory.A_CLASS
        )

        dep2 = DataDependency(
            local_path="/test2",
            mount_path="A/test2",
            file_hash="hash2",
            file_size=200,
            category=DependencyCategory.B_CLASS
        )

        dep_set.a_class_dependencies.append(dep1)
        dep_set.b_class_dependencies.append(dep2)
        dep_set.file_hashes.add("hash1")
        dep_set.file_hashes.add("hash2")

        assert len(dep_set.file_hashes) == 2
        assert dep_set.total_a_b_size == 300

    def test_file_tree_node(self):
        """测试FileTreeNode"""
        from desam_client.file_transfer.models import FileTreeNode

        # 创建叶子节点
        leaf = FileTreeNode(
            path="test.txt",
            file_hash="abc123",
            is_file=True
        )

        assert leaf.path == "test.txt"
        assert leaf.file_hash == "abc123"
        assert leaf.is_file is True

        # 创建目录节点
        dir_node = FileTreeNode(
            path="models",
            is_file=False
        )

        assert dir_node.path == "models"
        assert dir_node.is_file is False

    def test_checksum_operations(self):
        """测试校验和操作"""
        from desam_client.file_transfer.checksum import (
            calculate_file_hash,
            get_file_size,
        )

        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            test_content = "Hello, World!"
            f.write(test_content)
            f.flush()

            try:
                # 测试文件哈希
                file_hash = calculate_file_hash(f.name)
                assert len(file_hash) == 64  # SHA256

                # 测试文件大小
                file_size = get_file_size(f.name)
                assert file_size == len(test_content.encode('utf-8'))
            finally:
                os.unlink(f.name)

    def test_compression_operations(self):
        """测试压缩操作"""
        from desam_client.file_transfer.compression import (
            compress_directory_to_zip,
            is_zip_file,
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建测试目录
            test_dir = os.path.join(tmpdir, "test_dir")
            os.makedirs(test_dir)

            # 创建测试文件
            with open(os.path.join(test_dir, "file1.txt"), 'w') as f:
                f.write("content1")

            with open(os.path.join(test_dir, "file2.txt"), 'w') as f:
                f.write("content2")

            # 压缩目录
            zip_path = compress_directory_to_zip(test_dir)

            # 验证ZIP文件
            assert os.path.exists(zip_path)
            assert is_zip_file(zip_path)

    def test_file_manager_initialization(self):
        """测试FileManager初始化"""
        from desam_client.file_transfer.manager import FileManager

        mock_client = Mock()
        mock_client.api_key = "test-key"
        mock_client.timeout = 30.0
        mock_client._stub = Mock()

        file_manager = FileManager(mock_client)

        assert file_manager._client == mock_client
        # 验证_get_stub方法正常工作
        assert file_manager._get_stub() == mock_client._stub

    def test_quota_info(self):
        """测试QuotaInfo"""
        from desam_client.file_transfer.models import QuotaInfo

        quota = QuotaInfo(
            total_quota=1024 * 1024 * 1024,  # 1GB
            used_quota=512 * 1024 * 1024,    # 512MB
            available_quota=512 * 1024 * 1024,  # 512MB
        )

        assert quota.total_quota == 1024 * 1024 * 1024
        assert quota.available_quota == 512 * 1024 * 1024


class TestExampleUsage:
    """测试使用示例"""

    def test_example_code_structure(self):
        """测试示例代码结构"""
        # 这个测试确保示例代码可以正常导入和执行

        # 1. 导入模块
        from desam_client import DeSAMClient
        from desam_client.file_transfer import (
            FileManager,
            FileTransferError,
            QuotaExceededError,
        )

        # 2. 创建客户端（模拟）
        # client = DeSAMClient(
        #     host='localhost',
        #     port=50051,
        #     api_key='test-key'
        # )

        # 3. 验证FileManager存在
        assert FileManager is not None
        assert FileTransferError is not None
        assert QuotaExceededError is not None

        # 4. 验证数据模型
        from desam_client.file_transfer.models import (
            DataDependency,
            DependencyCategory,
            FileInfo,
            FileTreeNode,
            QuotaInfo,
        )

        assert DataDependency is not None
        assert DependencyCategory is not None
        assert FileInfo is not None
        assert FileTreeNode is not None
        assert QuotaInfo is not None


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
