"""统一的大模型调用封装。

本模块屏蔽底层 HTTP 细节，向业务层提供统一的文本对话接口。
当前仅支持 OpenAI Chat Completions 兼容接口的文本请求/文本响应，
不实现工具调用、Agent 或复杂多模态能力。

错误处理约定：
- 所有可预期错误统一抛 ModelCallError（AppError 子类），并给出不泄露密钥的可读信息。
- 上层只需捕获 ModelCallError 或 AppError 即可获得统一错误响应。
"""
from typing import TypedDict

import httpx

from app.core.exceptions import AppError
from app.core.logger import get_logger

logger = get_logger(__name__)


class ModelCallError(AppError):
    """模型调用错误，携带对用户可读的错误信息。

    status_code 与业务 code 保持一致，便于前端识别。
    """

    def __init__(
        self,
        message: str,
        *,
        code: int = 502,
        status_code: int = 502,
    ) -> None:
        super().__init__(message, code=code, status_code=status_code)


class ChatMessage(TypedDict):
    """一条对话消息。"""

    role: str  # system / user / assistant
    content: str


class LLMClient:
    """针对单个模型配置的对话客户端，供业务模块便捷调用。

    示例：
        client = LLMClient(
            base_url="https://api.example.com/v1",
            api_key="sk-xxx",
            model="gpt-4o-mini",
            timeout=60,
        )
        reply = client.chat([{"role": "user", "content": "你好"}])
    """

    def __init__(
        self,
        base_url: str,
        api_key: str | None,
        model: str,
        timeout: int = 60,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.timeout = timeout

    def chat(self, messages: list[ChatMessage]) -> str:
        """发送文本对话请求，返回模型文本响应。"""
        self._validate()

        url = f"{self.base_url}/chat/completions"
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        payload = {
            "model": self.model,
            "messages": messages,
            # 仅要求文本输出
            "stream": False,
        }

        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.post(url, json=payload, headers=headers)
        except httpx.TimeoutException:
            raise ModelCallError(f"模型调用超时（>{self.timeout}s），请检查模型是否可用或增大超时时间", code=504, status_code=504)
        except httpx.NetworkError:
            raise ModelCallError(f"无法连接到模型服务：{self.base_url}", code=502, status_code=502)
        except Exception:
            logger.exception("模型调用发生未预期网络异常")
            raise ModelCallError("模型调用发生未预期错误", code=500, status_code=500)

        return self._parse_response(resp)

    def _validate(self) -> None:
        missing = []
        if not self.base_url or not self.base_url.startswith(("http://", "https://")):
            missing.append("API Base URL 无效")
        if not self.model:
            missing.append("模型名称不能为空")
        if missing:
            raise ModelCallError("；".join(missing), code=422, status_code=422)

    def _parse_response(self, resp: httpx.Response) -> str:
        status = resp.status_code
        # 鉴权失败：不泄露 key，仅提示凭证
        if status in (401, 403):
            raise ModelCallError("模型鉴权失败，请检查 API Key 是否正确", code=401, status_code=401)
        if status == 404:
            raise ModelCallError("模型接口或地址不存在，请检查 API Base URL 与模型名称", code=404, status_code=404)
        if status == 422:
            raise ModelCallError("模型请求参数不合法，请检查模型名称与请求内容", code=422, status_code=422)
        if status == 429:
            raise ModelCallError("模型服务限流（429），请稍后重试", code=429, status_code=429)
        if status >= 500:
            raise ModelCallError(f"模型服务异常（HTTP {status}），请稍后重试", code=502, status_code=502)
        if status != 200:
            raise ModelCallError(f"模型调用失败（HTTP {status}）", code=502, status_code=502)

        try:
            data = resp.json()
        except Exception:
            logger.warning("模型返回非 JSON 响应")
            raise ModelCallError("模型返回了无法解析的响应", code=502, status_code=502)

        try:
            content = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError):
            logger.warning("模型响应缺少内容字段")
            raise ModelCallError("模型响应格式不符合预期", code=502, status_code=502)

        return content if isinstance(content, str) else str(content)
