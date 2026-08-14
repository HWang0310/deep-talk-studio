"""Production-local whisper.cpp bootstrap and transcription provider.

The selection Gate proved that official whisper.cpp full JSON contains direct
token offsets.  This module owns the boring machine work around that evidence:
pinning a compatible runtime/model, keeping them outside Git, verifying their
digests, and invoking the runtime once for each existing transcription chunk.
No cloud credential or fallback path is consulted here.
"""

import json
import os
import platform
import re
import shutil
import subprocess
import tempfile
import time
import urllib.request
import urllib.error
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, Mapping, Optional, Tuple

from ..narration_media import canonical_digest, sha256_file
from ..transcription_chunking import LOCAL_PROFILE_PATH, TranscriptionChunkPlan
from .base import (
    ProviderTimedUnit,
    ProviderTranscript,
    TranscriptionProviderError,
    boundary_risks_from_plan,
    validate_provider_units,
)
from .local_asr_selection import inspect_whisper_cpp_token_overlaps, parse_whisper_cpp_json


WHISPER_CPP_VERSION = "1.9.2"
WHISPER_CPP_SOURCE_COMMIT = "306c88f4d1286aec1bf96e544632897886af5501"
WHISPER_CPP_SOURCE_URL = "https://github.com/ggml-org/whisper.cpp.git"
WHISPER_CPP_SOURCE_ARCHIVE_URL = (
    "https://github.com/ggml-org/whisper.cpp/archive/refs/tags/v1.9.2.tar.gz"
)
WHISPER_CPP_MODEL_URL = "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-large-v3.bin"
WHISPER_CPP_MODEL_SHA256 = "64d182b440b98d5203c4f9bd541544d84c605196c4f7b845dfa11fb23594d1e2"
WHISPER_CPP_MODEL_BYTES = 3095033483
WHISPER_CPP_MODEL_NAME = "large-v3"
WHISPER_CPP_DTW_PRESET = "large.v3"


class WhisperCppBootstrapError(TranscriptionProviderError):
    """A verified local whisper.cpp installation cannot be prepared safely."""


class WhisperCppTokenOverlapError(WhisperCppBootstrapError):
    """Runtime raw token evidence overlaps and cannot form a canonical timeline."""

    def __init__(self, overlaps, raw_response_digests):
        super().__init__("whisper.cpp token offsets overlap，已停止，不修改或裁剪真实时间")
        self.overlaps = tuple(dict(item) for item in overlaps)
        self.raw_response_digests = tuple(str(value) for value in raw_response_digests)


@dataclass(frozen=True)
class WhisperCppRuntimeSpec:
    version: str = WHISPER_CPP_VERSION
    source_commit: str = WHISPER_CPP_SOURCE_COMMIT
    model_name: str = WHISPER_CPP_MODEL_NAME
    model_sha256: str = WHISPER_CPP_MODEL_SHA256
    model_bytes: int = WHISPER_CPP_MODEL_BYTES
    dtw_preset: str = WHISPER_CPP_DTW_PRESET
    source_url: str = WHISPER_CPP_SOURCE_URL
    source_archive_url: str = WHISPER_CPP_SOURCE_ARCHIVE_URL
    model_url: str = WHISPER_CPP_MODEL_URL


@dataclass(frozen=True)
class WhisperCppInstallation:
    runtime_path: Path
    model_path: Path
    provenance_path: Path
    cache_root: Path
    runtime_version: str
    source_commit: str
    build_identity: str
    model_name: str
    model_sha256: str
    model_bytes: int
    dtw_preset: str
    acceleration: str
    bootstrap_status: str


def production_transcription_cache_root(root: Optional[Path] = None) -> Path:
    """Return the stable user-level cache namespace for production ASR.

    ``root`` exists for tests and controlled application embeddings.  Ordinary
    users get a platform-neutral user cache without configuring an environment
    variable or knowing where the files live.
    """

    if root is None:
        return (Path.home() / ".cache" / "deep-talk-studio" / "transcription").resolve()
    base = Path(root).expanduser()
    if base.name != "transcription":
        base = base / "transcription"
    return base.resolve()


def _runtime_version_from_output(value: str) -> str:
    match = re.search(r"(?:version\s*:\s*|whisper\.cpp\s+)(\d+\.\d+\.\d+)", value)
    if match:
        return match.group(1)
    match = re.search(r"\b(\d+\.\d+\.\d+)\b", value)
    return match.group(1) if match else ""


def _system_https_proxy() -> Optional[str]:
    """Read an enabled macOS HTTPS proxy when this process lacks proxy env.

    The desktop app does not always inherit shell proxy variables, although the
    user may have enabled the macOS system proxy.  This only affects the
    official model download transport; it never changes model identity.
    """

    if any(os.environ.get(name) for name in ("HTTPS_PROXY", "https_proxy", "ALL_PROXY", "all_proxy")):
        return None
    if platform.system() != "Darwin":
        return None
    try:
        result = subprocess.run(
            ["scutil", "--proxy"], check=True, capture_output=True, text=True
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    output = result.stdout
    enabled = re.search(r"\bHTTPSEnable\s*:\s*1\b", output)
    host = re.search(r"\bHTTPSProxy\s*:\s*([^\s]+)", output)
    port = re.search(r"\bHTTPSPort\s*:\s*(\d+)", output)
    if not enabled or not host or not port:
        return None
    return f"http://{host.group(1)}:{port.group(1)}"


class WhisperCppBootstrap:
    """Discover or prepare one pinned, digest-verified whisper.cpp install."""

    def __init__(
        self,
        *,
        spec: WhisperCppRuntimeSpec = WhisperCppRuntimeSpec(),
        cache_root: Optional[Path] = None,
        runtime_builder: Optional[Callable[[Path, Path], None]] = None,
        model_downloader: Optional[Callable[[Path, str], None]] = None,
        runtime_version_reader: Optional[Callable[[Path], str]] = None,
        command_runner: Callable[..., Any] = subprocess.run,
    ):
        self.spec = spec
        self.cache_root = production_transcription_cache_root(cache_root)
        self._runtime_builder = runtime_builder
        self._model_downloader = model_downloader
        self._runtime_version_reader = runtime_version_reader or self._read_runtime_version
        self._run = command_runner

    @property
    def runtime_path(self) -> Path:
        return (
            self.cache_root
            / "runtimes"
            / f"whisper.cpp-{self.spec.version}-{platform.machine()}"
            / "bin"
            / "whisper-cli"
        )

    @property
    def model_path(self) -> Path:
        return (
            self.cache_root
            / "models"
            / f"whisper.cpp-{self.spec.version}-{self.spec.model_name}"
            / f"ggml-{self.spec.model_name}.bin"
        )

    @property
    def provenance_path(self) -> Path:
        return (
            self.cache_root
            / "provenance"
            / f"whisper.cpp-{self.spec.version}-{self.spec.model_name}.json"
        )

    def ensure(self) -> WhisperCppInstallation:
        self.cache_root.mkdir(parents=True, exist_ok=True)
        self._ensure_model()
        self._ensure_runtime()
        runtime_version = _runtime_version_from_output(
            str(self._runtime_version_reader(self.runtime_path))
        )
        if runtime_version != self.spec.version:
            raise WhisperCppBootstrapError(
                f"whisper.cpp runtime 版本不受支持：需要 {self.spec.version}，实际 {runtime_version or '未知'}"
            )
        model_sha = sha256_file(self.model_path)
        model_bytes = self.model_path.stat().st_size
        if model_sha != self.spec.model_sha256 or model_bytes != self.spec.model_bytes:
            raise WhisperCppBootstrapError(f"本地 {self.spec.model_name} 模型校验失败，已停止使用")
        runtime_sha = sha256_file(self.runtime_path)
        build_identity = f"{self.spec.version}+runtime-sha256:{runtime_sha}"
        acceleration = self._acceleration()
        provenance = {
            "artifact_version": "whisper-cpp-installation/1",
            "runtime_version": runtime_version,
            "source_commit": self.spec.source_commit,
            "runtime_path": str(self.runtime_path),
            "runtime_sha256": runtime_sha,
            "runtime_bytes": self.runtime_path.stat().st_size,
            "runtime_build_identity": build_identity,
            "model": self.spec.model_name,
            "model_path": str(self.model_path),
            "model_sha256": model_sha,
            "model_bytes": model_bytes,
            "dtw_preset": self.spec.dtw_preset,
            "cache_path": str(self.cache_root),
            "acceleration": acceleration,
            "bootstrap_status": "verified",
        }
        self.provenance_path.parent.mkdir(parents=True, exist_ok=True)
        self.provenance_path.write_text(
            json.dumps(provenance, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        return WhisperCppInstallation(
            runtime_path=self.runtime_path,
            model_path=self.model_path,
            provenance_path=self.provenance_path,
            cache_root=self.cache_root,
            runtime_version=runtime_version,
            source_commit=self.spec.source_commit,
            build_identity=build_identity,
            model_name=self.spec.model_name,
            model_sha256=model_sha,
            model_bytes=model_bytes,
            dtw_preset=self.spec.dtw_preset,
            acceleration=acceleration,
            bootstrap_status="verified",
        )

    def _ensure_model(self) -> None:
        if self.model_path.exists():
            self._verify_model()
            return
        self.model_path.parent.mkdir(parents=True, exist_ok=True)
        partial = self.model_path.with_suffix(self.model_path.suffix + ".part")
        if partial.exists():
            partial.unlink()
        downloader = self._model_downloader or self._download_model
        try:
            downloader(partial, self.spec.model_url)
        except Exception as exc:
            if partial.exists():
                partial.unlink()
            raise WhisperCppBootstrapError("正在准备本地语音识别模型时下载失败") from exc
        try:
            partial.replace(self.model_path)
        except OSError as exc:
            raise WhisperCppBootstrapError("本地语音识别模型无法保存到用户缓存") from exc
        self._verify_model()

    def _verify_model(self) -> None:
        actual_sha = sha256_file(self.model_path)
        actual_bytes = self.model_path.stat().st_size
        if actual_sha != self.spec.model_sha256 or actual_bytes != self.spec.model_bytes:
            raise WhisperCppBootstrapError(
                f"本地 {self.spec.model_name} 模型的 SHA-256 或文件大小不匹配，已拒绝运行"
            )

    def _ensure_runtime(self) -> None:
        if self.runtime_path.exists():
            if not self.runtime_path.is_file():
                raise WhisperCppBootstrapError("whisper.cpp runtime 路径不是文件")
            return
        self.runtime_path.parent.mkdir(parents=True, exist_ok=True)
        source_root = self.cache_root / "sources" / f"whisper.cpp-{self.spec.version}"
        builder = self._runtime_builder or self._build_runtime
        try:
            builder(self.runtime_path, source_root)
        except WhisperCppBootstrapError:
            raise
        except Exception as exc:
            raise WhisperCppBootstrapError("正在准备本地语音识别运行时失败") from exc
        if not self.runtime_path.is_file():
            raise WhisperCppBootstrapError("本地语音识别运行时准备后仍然不存在")
        try:
            self.runtime_path.chmod(self.runtime_path.stat().st_mode | 0o111)
        except OSError as exc:
            raise WhisperCppBootstrapError("本地语音识别运行时不可执行") from exc

    def _read_runtime_version(self, path: Path) -> str:
        try:
            result = self._run([str(path), "--version"], check=True, capture_output=True, text=True)
        except (OSError, subprocess.CalledProcessError) as exc:
            raise WhisperCppBootstrapError("无法验证 whisper.cpp runtime 版本") from exc
        output = f"{getattr(result, 'stdout', '')}\n{getattr(result, 'stderr', '')}"
        return _runtime_version_from_output(output)

    def _download_model(self, target: Path, url: str) -> None:
        curl = shutil.which("curl")
        if curl:
            command = [curl, "--location", "--fail", "--retry", "3"]
            proxy = _system_https_proxy()
            if proxy:
                command.extend(["--proxy", proxy])
            command.extend(["--output", str(target), url])
            self._run(
                command,
                check=True,
                capture_output=True,
                text=True,
            )
            return
        try:
            with urllib.request.urlopen(url, timeout=120) as source, target.open("wb") as sink:
                shutil.copyfileobj(source, sink, length=1024 * 1024)
        except (OSError, urllib.error.URLError) as exc:
            raise WhisperCppBootstrapError("系统没有可用的模型下载通道") from exc

    def _build_runtime(self, runtime_path: Path, source_root: Path) -> None:
        self._acquire_source(source_root)
        cmake = shutil.which("cmake")
        if not cmake:
            brew = shutil.which("brew")
            if brew:
                self._run([brew, "install", "cmake"], check=True)
                cmake = shutil.which("cmake")
        if not cmake:
            raise WhisperCppBootstrapError("系统缺少可自动准备的 CMake 构建工具")
        build_root = source_root / "build-production"
        configure = [
            cmake,
            "-S",
            str(source_root),
            "-B",
            str(build_root),
            "-DCMAKE_BUILD_TYPE=Release",
            "-DWHISPER_BUILD_TESTS=OFF",
            "-DWHISPER_BUILD_EXAMPLES=ON",
            "-DWHISPER_BUILD_SERVER=OFF",
            "-DGGML_METAL=ON" if platform.system() == "Darwin" else "-DGGML_METAL=OFF",
        ]
        self._run(configure, check=True, capture_output=True, text=True)
        self._run(
            [cmake, "--build", str(build_root), "--config", "Release", "--target", "whisper-cli"],
            check=True,
            capture_output=True,
            text=True,
        )
        built = build_root / "bin" / "whisper-cli"
        if not built.is_file():
            raise WhisperCppBootstrapError("CMake 构建完成但未找到 whisper-cli")
        shutil.copy2(built, runtime_path)
        for library in built.parent.glob("*.dylib"):
            shutil.copy2(library, runtime_path.parent / library.name)

    def _acquire_source(self, source_root: Path) -> None:
        if source_root.exists():
            git_dir = source_root / ".git"
            if git_dir.is_dir():
                try:
                    result = self._run(
                        ["git", "-C", str(source_root), "rev-parse", "HEAD"],
                        check=True,
                        capture_output=True,
                        text=True,
                    )
                    if result.stdout.strip() == self.spec.source_commit:
                        return
                except (OSError, subprocess.CalledProcessError):
                    pass
            raise WhisperCppBootstrapError("缓存中的 whisper.cpp 源码版本与 V1 锁定版本不一致")
        source_root.parent.mkdir(parents=True, exist_ok=True)
        git = shutil.which("git")
        if git:
            self._run(
                [git, "clone", "--depth", "1", "--branch", f"v{self.spec.version}", self.spec.source_url, str(source_root)],
                check=True,
                capture_output=True,
                text=True,
            )
            result = self._run(
                [git, "-C", str(source_root), "rev-parse", "HEAD"],
                check=True,
                capture_output=True,
                text=True,
            )
            if result.stdout.strip() != self.spec.source_commit:
                raise WhisperCppBootstrapError("下载的 whisper.cpp 源码版本校验失败")
            return
        curl = shutil.which("curl")
        tar = shutil.which("tar")
        if not curl or not tar:
            raise WhisperCppBootstrapError("系统没有可自动准备 whisper.cpp 源码的下载工具")
        archive = source_root.parent / f"whisper.cpp-{self.spec.version}.tar.gz"
        self._run(
            [curl, "--location", "--fail", "--retry", "3", "--output", str(archive), self.spec.source_archive_url],
            check=True,
            capture_output=True,
            text=True,
        )
        self._run(
            [tar, "-xzf", str(archive), "-C", str(source_root.parent)],
            check=True,
            capture_output=True,
            text=True,
        )
        extracted_default = source_root.parent / f"whisper.cpp-{self.spec.version}"
        if not extracted_default.is_dir():
            raise WhisperCppBootstrapError("下载的 whisper.cpp 源码目录不完整")
        if extracted_default != source_root:
            extracted_default.replace(source_root)
        archive.unlink(missing_ok=True)

    @staticmethod
    def _acceleration() -> str:
        if platform.system() == "Darwin" and platform.machine().lower() in {"arm64", "aarch64"}:
            return "Apple Silicon Metal"
        return "CPU"


class LocalWhisperCppTranscriptionProvider:
    """Run verified local whisper.cpp and preserve runtime token timestamps."""

    provider_name = "whisper.cpp"
    default_configured_model = WHISPER_CPP_MODEL_NAME
    default_dtw_preset = WHISPER_CPP_DTW_PRESET
    chunk_profile_path = LOCAL_PROFILE_PATH
    preferred_sample_rate = 24000

    def __init__(
        self,
        *,
        bootstrap: Optional[WhisperCppBootstrap] = None,
        runner: Callable[..., Any] = subprocess.run,
        clock: Callable[[], float] = time.perf_counter,
        threads: Optional[int] = None,
    ):
        self.bootstrap = bootstrap or WhisperCppBootstrap()
        self._run = runner
        self._clock = clock
        self._threads = threads or max(1, min(8, os.cpu_count() or 1))

    def transcribe(
        self,
        extracted_audio_artifact: Dict[str, Any],
        chunk_plan: TranscriptionChunkPlan,
        language: str,
        configured_model: str,
    ) -> ProviderTranscript:
        if configured_model != self.default_configured_model:
            raise WhisperCppBootstrapError(
                f"V1 本地转写只允许锁定的 {self.default_configured_model} 模型"
            )
        installation = self.bootstrap.ensure()
        run_root = installation.cache_root / "runs"
        run_root.mkdir(parents=True, exist_ok=True)
        units = []
        response_digests = []
        chunk_evidence = []
        overlaps = []
        provider_order = 0
        started = self._clock()
        with tempfile.TemporaryDirectory(prefix="whisper-cpp-", dir=str(run_root)) as temp:
            temp_root = Path(temp)
            for chunk in chunk_plan.chunks:
                output_base = temp_root / f"chunk-{chunk.chunk_index:04d}"
                command = [
                    str(installation.runtime_path),
                    "--model",
                    str(installation.model_path),
                    "--file",
                    str(chunk.path),
                    "--language",
                    language,
                    "--dtw",
                    installation.dtw_preset,
                    "--output-json-full",
                    "--output-file",
                    str(output_base),
                    "--no-prints",
                    "--threads",
                    str(self._threads),
                ]
                try:
                    result = self._run(command, check=True, capture_output=True, text=True)
                except (OSError, subprocess.CalledProcessError) as exc:
                    raise WhisperCppBootstrapError("本地语音识别运行失败，未回退到云端") from exc
                json_path = output_base.with_suffix(".json")
                if not json_path.is_file():
                    raise WhisperCppBootstrapError("whisper.cpp 没有生成可验证的 JSON 时间证据")
                try:
                    parsed = parse_whisper_cpp_json(
                        json_path,
                        chunk_index=chunk.chunk_index,
                        model_version=installation.runtime_version,
                        dtw_preset=installation.dtw_preset,
                        chunk_plan=chunk_plan,
                        provider_order_start=provider_order,
                        provider_request_id="local-whisper-cpp",
                    )
                except TranscriptionProviderError as exc:
                    raise WhisperCppBootstrapError(
                        "whisper.cpp 输出缺少真实 token 时间戳，已停止，不使用伪造时间"
                    ) from exc
                units.extend(parsed.units)
                overlaps.extend(
                    inspect_whisper_cpp_token_overlaps(
                        json_path,
                        chunk_index=chunk.chunk_index,
                        provider_order_start=provider_order,
                        model=installation.model_name,
                        dtw_preset=installation.dtw_preset,
                        runtime_version=installation.runtime_version,
                    )
                )
                provider_order += len(parsed.units)
                response_digests.append(parsed.raw_response_digest)
                chunk_evidence.append(
                    {
                        "chunk_index": chunk.chunk_index,
                        "unit_count": len(parsed.units),
                        "response_digest": parsed.raw_response_digest,
                        "stderr_digest": canonical_digest(getattr(result, "stderr", "")),
                        "stdout_digest": canonical_digest(getattr(result, "stdout", "")),
                    }
                )
        if not units:
            raise WhisperCppBootstrapError("whisper.cpp 没有识别出可绑定时间的 token")
        if overlaps:
            raise WhisperCppTokenOverlapError(overlaps, response_digests)
        previous_chunk = None
        previous_end = None
        for unit in units:
            if previous_chunk != unit.chunk_index:
                previous_chunk = unit.chunk_index
                previous_end = None
            if previous_end is not None and unit.local_start_seconds < previous_end:
                raise WhisperCppBootstrapError(
                    "whisper.cpp token offsets overlap，已停止，不修改或裁剪真实时间"
                )
            previous_end = unit.local_end_seconds
        validate_provider_units(units, chunk_plan)
        elapsed = self._clock() - started
        audio_digest = str(extracted_audio_artifact.get("artifact_digest") or "")
        metadata = {
            "source": "local_whisper_cpp_runtime",
            "provider_identity": self.provider_name,
            "runtime_version": installation.runtime_version,
            "runtime_source_commit": installation.source_commit,
            "runtime_build_identity": installation.build_identity,
            "runtime_path": str(installation.runtime_path),
            "model": installation.model_name,
            "model_sha256": installation.model_sha256,
            "model_bytes": installation.model_bytes,
            "cache_path": str(installation.cache_root),
            "bootstrap_status": installation.bootstrap_status,
            "acceleration": installation.acceleration,
            "language": language,
            "inference_parameters": {
                "dtw": installation.dtw_preset,
                "timestamp_granularity": "token",
                "threads": self._threads,
                "flash_attention": "runtime disables it for DTW token timestamps",
            },
            "timestamp_provenance": "whisper.cpp runtime token offsets from full JSON",
            "timestamp_granularity": "token",
            "extracted_audio_digest": audio_digest,
            "chunk_plan_digest": chunk_plan.digest,
            "chunk_evidence": chunk_evidence,
            "response_digests": response_digests,
            "runtime_seconds": round(elapsed, 6),
            "rtf": self._rtf(extracted_audio_artifact, elapsed),
        }
        return ProviderTranscript(
            provider=self.provider_name,
            provider_model=installation.model_name,
            provider_model_version=f"{installation.runtime_version}+{installation.source_commit}",
            provider_request_id="local-whisper-cpp",
            language=language,
            timestamp_granularity="token",
            units=tuple(units),
            boundary_risks=boundary_risks_from_plan(chunk_plan),
            raw_metadata=metadata,
            raw_response_digest=canonical_digest(response_digests),
            chunk_plan_digest=chunk_plan.digest,
        )

    @staticmethod
    def _rtf(extracted: Mapping[str, Any], elapsed: float) -> str:
        try:
            duration = float(extracted.get("duration_seconds") or 0)
        except (TypeError, ValueError):
            duration = 0.0
        if duration <= 0:
            return ""
        return f"{elapsed / duration:.6f}"


def resolve_default_transcription_provider() -> LocalWhisperCppTranscriptionProvider:
    """Return the only V1 production provider; it never inspects API keys."""

    return LocalWhisperCppTranscriptionProvider()


__all__ = [
    "LocalWhisperCppTranscriptionProvider",
    "WhisperCppBootstrap",
    "WhisperCppBootstrapError",
    "WhisperCppInstallation",
    "WhisperCppRuntimeSpec",
    "WhisperCppTokenOverlapError",
    "WHISPER_CPP_MODEL_BYTES",
    "WHISPER_CPP_DTW_PRESET",
    "WHISPER_CPP_MODEL_NAME",
    "WHISPER_CPP_MODEL_SHA256",
    "WHISPER_CPP_SOURCE_COMMIT",
    "WHISPER_CPP_VERSION",
    "production_transcription_cache_root",
    "resolve_default_transcription_provider",
]
