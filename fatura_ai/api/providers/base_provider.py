"""Abstract provider interface — all AI providers inherit from this."""
from abc import ABC, abstractmethod
from typing import Dict, Any


class BaseProvider(ABC):

    @abstractmethod
    def extract_invoice(self, file_url: str) -> Dict[str, Any]:
        """Extract invoice fields from file_url. Must return a structured dict."""
