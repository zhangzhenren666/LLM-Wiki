"""模型配置 Pydantic 模型。"""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ModelConfigCreate(BaseModel):
    """创建模型配置请求。

    api_key 可省略；配置合法地址与密钥后即可测试连接。
    """

    model_config = ConfigDict(protected_namespaces=())

    name: str = Field(..., description="配置名称")
    base_url: str = Field(..., description="OpenAI Chat Completions 兼容的 API Base URL")
    api_key: str | None = Field(None, description="API Key（可选）")
    model_name: str = Field(..., description="模型名称")
    timeout_seconds: int | None = Field(None, ge=1, le=600, description="请求超时时间（秒）")
    is_active: bool | None = Field(True, description="是否启用")
    is_default: bool | None = Field(False, description="是否为默认配置")

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("配置名称不能为空")
        return stripped

    @field_validator("base_url")
    @classmethod
    def base_url_valid(cls, v: str) -> str:
        v = v.strip().rstrip("/")
        if not v.startswith(("http://", "https://")):
            raise ValueError("API Base URL 必须是 http(s) 地址")
        return v

    @field_validator("model_name")
    @classmethod
    def model_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("模型名称不能为空")
        return v


class ModelConfigUpdate(BaseModel):
    """更新模型配置请求（所有字段可选）。

    api_key 为空字符串时表示不修改；传入非空值则覆盖。
    """

    model_config = ConfigDict(protected_namespaces=())

    name: str | None = Field(None, description="配置名称")
    base_url: str | None = Field(None, description="API Base URL")
    api_key: str | None = Field(None, description="API Key（留空表示不修改）")
    model_name: str | None = Field(None, description="模型名称")
    timeout_seconds: int | None = Field(None, ge=1, le=600, description="请求超时时间（秒）")
    is_active: bool | None = Field(None, description="是否启用")
    is_default: bool | None = Field(None, description="是否为默认配置")

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v: str | None) -> str | None:
        if v is None:
            return v
        stripped = v.strip()
        if not stripped:
            raise ValueError("配置名称不能为空")
        return stripped

    @field_validator("base_url")
    @classmethod
    def base_url_valid(cls, v: str | None) -> str | None:
        if v is None:
            return v
        v = v.strip().rstrip("/")
        if not v.startswith(("http://", "https://")):
            raise ValueError("API Base URL 必须是 http(s) 地址")
        return v

    @field_validator("model_name")
    @classmethod
    def model_not_empty(cls, v: str | None) -> str | None:
        if v is None:
            return v
        v = v.strip()
        if not v:
            raise ValueError("模型名称不能为空")
        return v


class ModelConfigRead(BaseModel):
    """模型配置响应模型。

    绝不包含 API Key 明文，仅暴露是否已配置，避免敏感信息泄露。
    """

    model_config = ConfigDict(from_attributes=True, protected_namespaces=())

    id: int
    name: str
    base_url: str
    model_name: str
    timeout_seconds: int
    is_active: bool
    is_default: bool
    api_key_configured: bool = False
    created_at: datetime
    updated_at: datetime


class ModelConfigTestResult(BaseModel):
    """测试连接结果。"""

    success: bool
    message: str
    reply: str | None = None
