"""密码哈希与校验（PBKDF2-SHA256）。

设计说明（面试点）：
- 只用标准库 hashlib + hmac + os：Windows / Python 3.13 下 bcrypt、argon2 等
  C 扩展库常因缺少编译好的 wheel 而安装失败，stdlib 方案零依赖风险
- 迭代次数 600,000 遵循 OWASP 对 PBKDF2-SHA256 的现行建议
- 盐 16 字节随机生成，每个密码独立加盐
- 存储格式：pbkdf2_sha256$迭代次数$盐hex$哈希hex（约 125 字符，users.password_hash
  的 VARCHAR(255) 留足余量）
- 比对用 hmac.compare_digest（常数时间比较，防时序侧信道）
"""
import hashlib
import hmac
import os

ALGORITHM = "pbkdf2_sha256"
ITERATIONS = 600_000
SALT_LENGTH = 16


def hash_password(password: str) -> str:
    salt = os.urandom(SALT_LENGTH)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, ITERATIONS)
    return f"{ALGORITHM}${ITERATIONS}${salt.hex()}${dk.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        algo, iters, salt_hex, hash_hex = stored.split("$")
        if algo != ALGORITHM:
            return False
        dk = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), bytes.fromhex(salt_hex), int(iters)
        )
        return hmac.compare_digest(dk.hex(), hash_hex)
    except (ValueError, TypeError):
        return False
