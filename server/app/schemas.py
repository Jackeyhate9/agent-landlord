from typing import Any, Literal

from pydantic import BaseModel, Field, HttpUrl, field_validator


Stake = Literal[100, 200, 500, 1000]


class JoinCodeView(BaseModel):
    code: str
    expires_at: str


class JoinStatusView(BaseModel):
    paired: bool
    agent_id: str | None = None
    agent_name: str | None = None
    model_label: str | None = None
    certified: bool = False
    queued: bool = False


class BridgeJoin(BaseModel):
    code: str = Field(pattern=r"^AL-[A-Z2-9]{4}-[A-Z2-9]{4}$")
    owner_public_key: str = Field(min_length=32, max_length=256)


class BridgeJoinV1(BaseModel):
    protocol_version: Literal[1]
    join_code: str = Field(pattern=r"^AL-[A-Z2-9]{4}-[A-Z2-9]{4}$")
    public_key: str = Field(min_length=32, max_length=128)
    signature: str = Field(min_length=64, max_length=256)
    adapter: str = Field(min_length=2, max_length=48)
    # 隐私友好的自动检测（可选）：仅运行时类型名与模型名标签
    detected_runtime: str | None = Field(default=None, max_length=48)
    detected_model: str | None = Field(default=None, max_length=48)


class BridgeActivation(BaseModel):
    agent_name: str | None = Field(default=None, min_length=2, max_length=32)
    model_label: str | None = Field(default=None, min_length=1, max_length=24)
    runtime_label: str | None = Field(default=None, min_length=1, max_length=32)
    max_stake: Stake = 100
    pov_allowed: bool = False
    auto_queue: bool = True


class AgentConfigure(BaseModel):
    agent_name: str = Field(min_length=2, max_length=32)
    model_label: str = Field(min_length=1, max_length=24)
    runtime_label: str = Field(min_length=1, max_length=32)
    avatar_url: HttpUrl | None = None
    max_stake: Stake = 100
    pov_allowed: bool = False

    @field_validator("agent_name", "model_label", "runtime_label")
    @classmethod
    def no_controls(cls, value: str) -> str:
        if any(ord(char) < 32 for char in value):
            raise ValueError("control characters are not allowed")
        return value.strip()


class CertificationResult(BaseModel):
    passed_tests: list[str] = Field(default_factory=list)


class QueueView(BaseModel):
    position: int
    agent_id: str
    agent_name: str
    model_label: str
    current_at: int
    pov_allowed: bool
    online: bool
    is_house: bool = False


class AdminLogin(BaseModel):
    password: str


class TokenAdjustment(BaseModel):
    agent_id: str
    operation: Literal["add", "subtract", "reset"]
    amount: int = Field(default=0, ge=0)
    reason: str = Field(min_length=3, max_length=240)


class PublicEvent(BaseModel):
    event_id: str
    game_id: str | None = None
    sequence: int
    type: str
    actor: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    created_at: str
    broadcast_at: str


class HealthView(BaseModel):
    status: Literal["ok", "degraded"]
    checks: dict[str, str]
