from abc import ABC, abstractmethod
from dataclasses import dataclass

@dataclass
class AIResponse:
    text: str
    provider: str
    tokens_used: int
    model: str
    from_cache: bool = False

class BaseProvider(ABC):
    @abstractmethod
    async def generate(self, prompt: str, system: str = '') -> AIResponse:
        pass
