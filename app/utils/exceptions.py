"""
自定义异常类
"""
from typing import Optional


class AppException(Exception):
    """应用自定义异常基类"""
    
    def __init__(
        self,
        message: str,
        error_code: int = 400,
        status_code: int = 400,
        detail: Optional[str] = None
    ):
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        self.detail = detail
        super().__init__(message)


class AuthenticationError(AppException):
    """认证错误"""
    
    def __init__(self, message: str = "认证失败", detail: Optional[str] = None):
        super().__init__(message, error_code=401, status_code=401, detail=detail)


class AuthorizationError(AppException):
    """授权错误"""
    
    def __init__(self, message: str = "权限不足", detail: Optional[str] = None):
        super().__init__(message, error_code=403, status_code=403, detail=detail)


class NotFoundError(AppException):
    """资源不存在错误"""
    
    def __init__(self, message: str = "资源不存在", detail: Optional[str] = None):
        super().__init__(message, error_code=404, status_code=404, detail=detail)


class ValidationError(AppException):
    """数据验证错误"""
    
    def __init__(self, message: str = "数据验证失败", detail: Optional[str] = None):
        super().__init__(message, error_code=422, status_code=422, detail=detail)


class BusinessError(AppException):
    """业务逻辑错误"""
    
    def __init__(self, message: str, detail: Optional[str] = None):
        super().__init__(message, error_code=400, status_code=400, detail=detail)


class PaymentError(AppException):
    """支付相关错误"""
    
    def __init__(self, message: str = "支付失败", detail: Optional[str] = None):
        super().__init__(message, error_code=402, status_code=400, detail=detail)


class RateLimitError(AppException):
    """频率限制错误"""
    
    def __init__(self, message: str = "请求频率过高", detail: Optional[str] = None):
        super().__init__(message, error_code=429, status_code=429, detail=detail) 