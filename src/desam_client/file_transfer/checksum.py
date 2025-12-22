"""文件校验和计算工具"""

import hashlib
import os
import mmap
from functools import lru_cache
from typing import Callable, Optional


# 缓存已计算的文件哈希
_file_hash_cache = {}
_cache_size = 100  # 最大缓存条目数


def calculate_file_hash(
    file_path: str,
    algorithm: str = "sha256",
    use_cache: bool = True,
    progress_callback: Optional[Callable[[int, int], None]] = None
) -> str:
    """计算文件校验和

    Args:
        file_path: 文件路径
        algorithm: 哈希算法（sha256, md5等）
        use_cache: 是否使用缓存（默认True）
        progress_callback: 进度回调函数(uploaded_bytes, total_bytes)

    Returns:
        str: 文件哈希值
    """
    # 检查缓存
    if use_cache and file_path in _file_hash_cache:
        cache_entry = _file_hash_cache[file_path]
        # 检查文件是否修改
        current_mtime = os.path.getmtime(file_path)
        if cache_entry['mtime'] == current_mtime:
            return cache_entry['hash']

    file_size = os.path.getsize(file_path)

    # 根据文件大小选择最优算法
    # 大文件使用内存映射加速
    if file_size > 100 * 1024 * 1024:  # > 100MB
        hash_value = _calculate_hash_mmap(file_path, algorithm, progress_callback)
    else:
        # 小文件使用分块读取，使用更大的分块
        hash_value = _calculate_hash_chunks(file_path, algorithm, file_size, progress_callback)

    # 更新缓存
    if use_cache:
        _update_cache(file_path, hash_value)

    return hash_value


def _calculate_hash_chunks(
    file_path: str,
    algorithm: str,
    file_size: int,
    progress_callback: Optional[Callable[[int, int], None]] = None
) -> str:
    """使用分块读取计算哈希（适合小文件）"""
    hash_func = hashlib.new(algorithm)

    # 根据文件大小动态调整分块大小
    if file_size < 1024 * 1024:  # < 1MB
        chunk_size = 128 * 1024  # 128KB (从64KB提升)
    elif file_size < 100 * 1024 * 1024:  # < 100MB
        chunk_size = 512 * 1024  # 512KB (从256KB提升)
    else:
        chunk_size = 2 * 1024 * 1024  # 2MB (从1MB提升)

    uploaded = 0
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(chunk_size), b''):
            hash_func.update(chunk)
            uploaded += len(chunk)
            if progress_callback:
                progress_callback(uploaded, file_size)

    return hash_func.hexdigest()


def _calculate_hash_mmap(
    file_path: str,
    algorithm: str,
    progress_callback: Optional[Callable[[int, int], None]] = None
) -> str:
    """使用内存映射计算哈希（适合大文件）"""
    hash_func = hashlib.new(algorithm)

    file_size = os.path.getsize(file_path)
    uploaded = 0

    with open(file_path, 'rb') as f:
        with mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as mmapped_file:
            # 内存映射读取大块数据
            chunk_size = 16 * 1024 * 1024  # 16MB chunks for mmap

            for i in range(0, len(mmapped_file), chunk_size):
                chunk = mmapped_file[i:i + chunk_size]
                hash_func.update(chunk)
                uploaded += len(chunk)
                if progress_callback:
                    progress_callback(uploaded, file_size)

    return hash_func.hexdigest()


def _update_cache(file_path: str, file_hash: str):
    """更新哈希缓存"""
    global _file_hash_cache

    # 如果缓存已满，删除最旧的条目
    if len(_file_hash_cache) >= _cache_size:
        oldest_key = next(iter(_file_hash_cache))
        del _file_hash_cache[oldest_key]

    _file_hash_cache[file_path] = {
        'hash': file_hash,
        'mtime': os.path.getmtime(file_path)
    }


def clear_hash_cache():
    """清除哈希缓存"""
    global _file_hash_cache
    _file_hash_cache.clear()


def calculate_directory_hash(
    dir_path: str,
    algorithm: str = "sha256",
    use_cache: bool = True,
    progress_callback: Optional[Callable[[int, int], None]] = None
) -> str:
    """计算目录校验和（递归计算所有文件）

    Args:
        dir_path: 目录路径
        algorithm: 哈希算法
        use_cache: 是否使用缓存（默认True）
        progress_callback: 进度回调函数(uploaded_bytes, total_bytes)

    Returns:
        str: 目录哈希值
    """
    hash_func = hashlib.new(algorithm)

    # 先计算目录总大小用于进度回调
    total_size = get_directory_size(dir_path)
    processed_size = 0

    # 按文件名排序确保一致性
    for root, dirs, files in os.walk(dir_path):
        dirs.sort()
        files.sort()

        for file_name in files:
            file_path = os.path.join(root, file_name)
            # 计算相对路径的哈希
            rel_path = os.path.relpath(file_path, dir_path)
            hash_func.update(rel_path.encode('utf-8'))

            # 计算文件内容的哈希
            file_size = os.path.getsize(file_path)

            if file_size > 100 * 1024 * 1024:  # > 100MB 使用内存映射
                with open(file_path, 'rb') as f:
                    with mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as mmapped_file:
                        chunk_size = 16 * 1024 * 1024  # 16MB
                        for i in range(0, len(mmapped_file), chunk_size):
                            chunk = mmapped_file[i:i + chunk_size]
                            hash_func.update(chunk)
            else:
                # 动态调整分块大小
                if file_size < 1024 * 1024:  # < 1MB
                    chunk_size = 128 * 1024  # 128KB
                elif file_size < 100 * 1024 * 1024:  # < 100MB
                    chunk_size = 512 * 1024  # 512KB
                else:
                    chunk_size = 2 * 1024 * 1024  # 2MB

                with open(file_path, 'rb') as f:
                    for chunk in iter(lambda: f.read(chunk_size), b''):
                        hash_func.update(chunk)

            # 更新进度
            processed_size += file_size
            if progress_callback:
                progress_callback(processed_size, total_size)

    return hash_func.hexdigest()


def get_file_size(file_path: str) -> int:
    """获取文件大小

    Args:
        file_path: 文件路径

    Returns:
        int: 文件大小（字节）
    """
    return os.path.getsize(file_path)


def get_directory_size(dir_path: str) -> int:
    """获取目录总大小

    Args:
        dir_path: 目录路径

    Returns:
        int: 目录总大小（字节）
    """
    total_size = 0
    for root, dirs, files in os.walk(dir_path):
        for file_name in files:
            file_path = os.path.join(root, file_name)
            total_size += os.path.getsize(file_path)

    return total_size
