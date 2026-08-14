"""Provider-neutral transcription adapters."""

from .base import (
    ProviderBoundaryRisk,
    ProviderTimedUnit,
    ProviderTranscript,
    TranscriptionProvider,
    TranscriptionProviderError,
)
from .deterministic import DeterministicTranscriptionProvider
from .local_whisper_cpp import (
    LocalWhisperCppTranscriptionProvider,
    WhisperCppBootstrap,
    WhisperCppBootstrapError,
    WhisperCppInstallation,
    WhisperCppRuntimeSpec,
    resolve_default_transcription_provider,
)

__all__ = [
    "DeterministicTranscriptionProvider",
    "LocalWhisperCppTranscriptionProvider",
    "ProviderBoundaryRisk",
    "ProviderTimedUnit",
    "ProviderTranscript",
    "TranscriptionProvider",
    "TranscriptionProviderError",
    "WhisperCppBootstrap",
    "WhisperCppBootstrapError",
    "WhisperCppInstallation",
    "WhisperCppRuntimeSpec",
    "resolve_default_transcription_provider",
]
