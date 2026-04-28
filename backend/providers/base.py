"""Base provider interface."""

from abc import ABC, abstractmethod

from ..schemas.provider import ProviderRequest, ProviderResponse


class Provider(ABC):
    """Minimal async interface for model providers."""

    name: str

    @abstractmethod
    async def complete(self, request: ProviderRequest) -> ProviderResponse:
        """Generate one completion for a normalized provider request."""
