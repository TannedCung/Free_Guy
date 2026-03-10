"""
Custom exception hierarchy for the Generative Agents simulation.

Usage:
  from exceptions import SimulationError, LLMError, MemoryError, MazeError
"""


class SimulationError(Exception):
    """Base exception for all simulation errors."""


class LLMError(SimulationError):
    """Raised when an LLM API call fails or returns an unexpected response."""


class LLMParseError(LLMError):
    """Raised when an LLM response cannot be parsed into the expected format."""


class LLMRequestError(LLMError):
    """Raised when an LLM API request itself fails (network, auth, etc.)."""


class MemoryError(SimulationError):
    """Raised when a memory operation fails (read, write, or lookup)."""


class MazeError(SimulationError):
    """Raised when a maze/world operation fails (invalid tile, path, etc.)."""


class PersonaError(SimulationError):
    """Raised when a persona operation fails."""


class FileOperationError(SimulationError):
    """Raised when a file I/O operation fails in the simulation context."""
