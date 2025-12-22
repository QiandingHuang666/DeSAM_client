"""文件传输功能测试"""

import os
import tempfile
import unittest
from unittest.mock import Mock, MagicMock, patch
import pytest

from desam_client.file_transfer.models import (
    DataDependency,
    DependencyCategory,
    DependencySet,
    FileInfo,
    FileTreeNode,
    QuotaInfo,
)
from desam_client.file_transfer.checksum import (
    calculate_file_hash,
    get_file_size,
)
from desam_client.file_transfer.compression import (
    compress_directory_to_zip,
    is_zip_file,
)
from desam_client.file_transfer.manager import FileManager, FileTransferError, QuotaExceededError


class TestFileTransferModels(unittest.TestCase):
    """测试数据模型"""

    def test_dependency_set_total_size(self):
        """测试DependencySet总大小计算"""
        dep_set = DependencySet()

        # 添加A类依赖
        dep_set.a_class_dependencies.append(DataDependency(
            local_path="/test1",
            mount_path="A/test1",
            file_hash="hash1",
            file_size=100,
            category=DependencyCategory.A_CLASS
        ))

        # 添加B类依赖
        dep_set.b_class_dependencies.append(DataDependency(
            local_path="/test2",
            mount_path="A/test2",
            file_hash="hash2",
            file_size=200,
            category=DependencyCategory.B_CLASS
        ))

        # 添加C类依赖（不计入总大小）
        dep_set.c_class_dependencies.append(DataDependency(
            local_path="/test3",
            mount_path="A/test3",
            file_hash="hash3",
            file_size=300,
            category=DependencyCategory.C_CLASS
        ))

        # A类+B类总大小应该是300
        assert dep_set.total_a_b_size == 300


class TestChecksum(unittest.TestCase):
    """测试校验和计算"""

    def test_calculate_file_hash(self):
        """测试文件哈希计算"""
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write("test content")
            f.flush()

            try:
                file_hash = calculate_file_hash(f.name)
                assert len(file_hash) == 64  # SHA256 length
                assert all(c in '0123456789abcdef' for c in file_hash)
            finally:
                os.unlink(f.name)

    def test_get_file_size(self):
        """测试获取文件大小"""
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            test_content = "test content"
            f.write(test_content)
            f.flush()

            try:
                file_size = get_file_size(f.name)
                assert file_size == len(test_content.encode('utf-8'))
            finally:
                os.unlink(f.name)


class TestCompression(unittest.TestCase):
    """测试压缩功能"""

    def test_compress_directory_to_zip(self):
        """测试目录压缩"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建测试目录和文件
            test_dir = os.path.join(tmpdir, "test_dir")
            os.makedirs(test_dir)

            with open(os.path.join(test_dir, "file1.txt"), 'w') as f:
                f.write("content1")

            with open(os.path.join(test_dir, "file2.txt"), 'w') as f:
                f.write("content2")

            # 压缩目录
            zip_path = compress_directory_to_zip(test_dir)

            # 验证ZIP文件存在
            assert os.path.exists(zip_path)
            assert is_zip_file(zip_path)


class TestFileManager(unittest.TestCase):
    """测试FileManager"""

    def setUp(self):
        """测试前准备"""
        # 创建模拟的DeSAMClient
        self.mock_client = Mock()
        self.mock_client.api_key = "test-api-key"
        self.mock_client.timeout = 30.0
        self.mock_client._stub = Mock()

        # 创建FileManager实例
        self.file_manager = FileManager(self.mock_client)

    def test_check_quota(self):
        """测试查询配额"""
        # 模拟gRPC响应
        mock_response = Mock()
        mock_response.response.success = True
        mock_response.total_quota = 1024 * 1024 * 1024
        mock_response.used_quota = 512 * 1024 * 1024
        mock_response.available_quota = 512 * 1024 * 1024

        self.mock_client._stub.QueryCacheQuota.return_value = mock_response

        # 调用方法
        quota = self.file_manager.check_quota()

        # 验证结果
        assert quota.total_quota == 1024 * 1024 * 1024
        assert quota.available_quota == 512 * 1024 * 1024

    def test_check_quota_failure(self):
        """测试查询配额失败"""
        # 模拟gRPC响应失败
        mock_response = Mock()
        mock_response.response.success = False
        mock_response.response.message = "Authentication failed"

        self.mock_client._stub.QueryCacheQuota.return_value = mock_response

        # 调用方法应该抛出异常
        with pytest.raises(FileTransferError, match="查询配额失败"):
            self.file_manager.check_quota()

    def test_upload_file_not_exists(self):
        """测试上传不存在的文件"""
        with pytest.raises(FileNotFoundError):
            self.file_manager.upload_file("/nonexistent/file.txt")

    @patch('builtins.open', new_callable=unittest.mock.mock_open, read_data=b'test content')
    @patch('os.path.exists', return_value=True)
    @patch('os.path.getsize', return_value=12)
    @patch('os.path.getmtime', return_value=1234567890.0)
    def test_upload_file_success(self, mock_exists, mock_getsize, mock_getmtime, mock_open):
        """测试文件上传成功"""
        # 模拟gRPC响应
        mock_response = Mock()
        mock_response.response.success = True
        mock_response.file_hash = "abc123"

        self.mock_client._stub.UploadFile.return_value = mock_response

        # 调用方法
        file_info = self.file_manager.upload_file("/test/file.txt")

        # 验证结果
        assert file_info.file_hash == "abc123"
        assert file_info.file_size == 12

    def test_build_file_tree(self):
        """测试构建文件树"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建测试文件
            test_file = os.path.join(tmpdir, "test.txt")
            with open(test_file, 'w') as f:
                f.write("test")

            # 构建文件树
            file_mappings = [(test_file, "A/test.txt")]
            tree = self.file_manager.build_file_tree(file_mappings)

            # 验证树结构
            assert tree.path == ""
            assert len(tree.children) > 0


if __name__ == '__main__':
    unittest.main()
