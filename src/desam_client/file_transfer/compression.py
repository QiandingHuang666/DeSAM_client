"""目录压缩工具"""

import os
import tempfile
import zipfile
from pathlib import Path
from typing import Optional


def compress_directory_to_zip(dir_path: str, output_path: Optional[str] = None) -> str:
    """将目录压缩为ZIP文件

    Args:
        dir_path: 要压缩的目录路径
        output_path: 输出ZIP文件路径（可选）

    Returns:
        str: 生成的ZIP文件路径
    """
    if output_path is None:
        # 在临时目录创建ZIP文件
        temp_dir = tempfile.gettempdir()
        dir_name = Path(dir_path).name
        output_path = os.path.join(temp_dir, f"{dir_name}.zip")

    with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(dir_path):
            for file_name in files:
                file_path = os.path.join(root, file_name)
                # 计算相对路径作为ZIP内的路径
                arcname = os.path.relpath(file_path, dir_path)
                zf.write(file_path, arcname)

    return output_path


def decompress_zip(zip_path: str, output_dir: str) -> None:
    """解压ZIP文件到目录

    Args:
        zip_path: ZIP文件路径
        output_dir: 输出目录
    """
    with zipfile.ZipFile(zip_path, 'r') as zf:
        zf.extractall(output_dir)


def is_zip_file(file_path: str) -> bool:
    """判断文件是否为ZIP格式

    Args:
        file_path: 文件路径

    Returns:
        bool: 是否为ZIP文件
    """
    try:
        with zipfile.ZipFile(file_path, 'r') as zf:
            zf.testzip()
        return True
    except zipfile.BadZipFile:
        return False
