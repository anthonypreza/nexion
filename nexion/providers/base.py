from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class Provider(ABC):
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key

    @abstractmethod
    async def chat(self, model: str, messages: List[Dict[str, Any]]) -> str:
        raise NotImplementedError("Must be implemented by subclass")
