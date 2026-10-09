"""凭据安全工具。

使用 Fernet 对 API Key 等敏感值进行对称加密，避免以明文形式落库。
密钥来自配置 setting.model_api_key_secret；未显式配置时从 jwt_secret 派生，
仅在开发/测试环境使用，生产环境必须显式设置 model_api_key_secret。
"""
import hashlib
from base64 import urlsafe_b64encode

from cryptography.fernet import Fernet

from app.core.config import settings
from app.core.logger import get_logger

logger = get_logger(__name__)


def _get_fernet() -> Fernet:
    """构建用于加解密的 Fernet 实例。"""
    secret = settings.model_api_key_secret or settings.jwt_secret
    # Fernet 需要 32 字节的 urlsafe base64 密钥，这里对任意 secret 做确定性哈希派生
    digest = hashlib.sha256(secret.encode("utf-8")).digest()
    key = urlsafe_b64encode(digest)
    return Fernet(key)


def encrypt_secret(plaintext: str) -> str:
    """加密敏感值，返回可用于数据库存储的密文。"""
    if not plaintext:
        return ""
    try:
        return _get_fernet().encrypt(plaintext.encode("utf-8")).decode("utf-8")
    except Exception:  # pragma: no cover - 防御性兜底，不允许抛到业务层
        logger.exception("加密敏感值失败")
        raise


def decrypt_secret(ciphertext: str | None) -> str | None:
    """解密数据库中的敏感值，返回明文；非法输入返回 None。"""
    if not ciphertext:
        return None
    try:
        return _get_fernet().decrypt(ciphertext.encode("utf-8")).decode("utf-8")
    except Exception:
        # 解密失败（密钥变更等）不应导致接口崩溃，按未配置处理
        logger.warning("解密敏感值失败，可能密钥已变更")
        return None
