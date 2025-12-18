"""DeSAM客户端异常定义"""


class DeSAMError(Exception):
    """DeSAM基础异常类"""

    pass


class AuthenticationError(DeSAMError):
    """认证失败异常（API Key无效）"""

    pass


class JobNotFoundError(DeSAMError):
    """作业不存在异常"""

    pass


class DeSAMConnectionError(DeSAMError):
    """连接失败异常"""

    pass


class SubmitError(DeSAMError):
    """作业提交失败异常"""

    pass
