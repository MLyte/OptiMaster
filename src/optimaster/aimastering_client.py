from __future__ import annotations

import json
import mimetypes
import os
import time
import uuid
from pathlib import Path
from typing import Callable
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from optimaster.config import AiMasteringConfig
from optimaster.errors import OperationCancelledError, RemoteMasteringError

ProgressCallback = Callable[[str, int], None]
CancelCallback = Callable[[], bool]


class AiMasteringClient:
    def __init__(self, config: AiMasteringConfig) -> None:
        self.config = config
        token = (config.access_token or os.environ.get(config.token_env, "")).strip()
        if not token:
            raise RemoteMasteringError(
                "AI Mastering token is missing",
                f"Set {config.token_env} before using the cloud engine.",
            )
        self._authorization = f"{config.auth_prefix} {token}".strip() if config.auth_prefix else token

    def master(
        self,
        input_path: Path,
        output_path: Path,
        target_lufs: float,
        output_format: str,
        true_peak_ceiling: float,
        progress_callback: ProgressCallback | None = None,
        cancel_callback: CancelCallback | None = None,
    ) -> Path:
        self._raise_if_cancelled(cancel_callback)
        self._notify(progress_callback, "Uploading source to AI Mastering", 48)
        audio = self._upload_audio(input_path)
        audio_id = self._required_id(audio, "uploaded audio")

        self._raise_if_cancelled(cancel_callback)
        self._notify(progress_callback, "Starting AI Mastering cloud job", 58)
        mastering = self._create_mastering(
            audio_id=audio_id,
            target_lufs=target_lufs,
            output_format=output_format,
            true_peak_ceiling=true_peak_ceiling,
        )
        mastering_id = self._required_id(mastering, "mastering job")

        mastering = self._wait_for_mastering(mastering_id, progress_callback, cancel_callback)
        output_audio_id = mastering.get("output_audio_id")
        if not isinstance(output_audio_id, int):
            raise RemoteMasteringError("AI Mastering job finished without an output audio id", json.dumps(mastering))

        self._raise_if_cancelled(cancel_callback)
        self._notify(progress_callback, "Downloading AI Mastering result", 86)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        self._download_audio(output_audio_id, output_path)
        self._notify(progress_callback, "AI Mastering download complete", 90)
        return output_path

    def _upload_audio(self, input_path: Path) -> dict[str, object]:
        fields: dict[str, str] = {"name": input_path.name}
        files = {"file": input_path}
        return self._multipart_json("POST", "/audios", fields, files)

    def create_mastering_job(
        self,
        input_path: Path,
        target_lufs: float,
        output_format: str,
        true_peak_ceiling: float,
        progress_callback: ProgressCallback | None = None,
        cancel_callback: CancelCallback | None = None,
    ) -> dict[str, object]:
        self._raise_if_cancelled(cancel_callback)
        self._notify(progress_callback, "Uploading source to AI Mastering", 86)
        audio = self._upload_audio(input_path)
        audio_id = self._required_id(audio, "uploaded audio")
        self._raise_if_cancelled(cancel_callback)
        self._notify(progress_callback, "Creating AI Mastering remote job", 90)
        mastering = self._create_mastering(
            audio_id=audio_id,
            target_lufs=target_lufs,
            output_format=output_format,
            true_peak_ceiling=true_peak_ceiling,
        )
        mastering["input_audio_id"] = audio_id
        return mastering

    def get_mastering(self, mastering_id: int) -> dict[str, object]:
        return self._json_request("GET", f"/masterings/{mastering_id}")

    def download_output(self, output_audio_id: int, output_path: Path) -> None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        self._download_audio(output_audio_id, output_path)

    def _create_mastering(
        self,
        audio_id: int,
        target_lufs: float,
        output_format: str,
        true_peak_ceiling: float,
    ) -> dict[str, object]:
        fields = {
            "input_audio_id": str(audio_id),
            "mode": "custom",
            "mastering": "true",
            "mastering_algorithm": "v2",
            "target_loudness": f"{target_lufs:.1f}",
            "target_loudness_mode": "loudness",
            "mastering_matching_level": "0.5",
            "bass_preservation": "true",
            "preset": self.config.preset,
            "ceiling": f"{true_peak_ceiling:.1f}",
            "ceiling_mode": "true_peak",
            "sample_rate": "44100",
            "bit_depth": str(self.config.bit_depth),
            "output_format": output_format,
        }
        return self._multipart_json("POST", "/masterings", fields, {})

    def _wait_for_mastering(
        self,
        mastering_id: int,
        progress_callback: ProgressCallback | None,
        cancel_callback: CancelCallback | None,
    ) -> dict[str, object]:
        started_at = time.monotonic()
        while True:
            self._raise_if_cancelled(cancel_callback)
            elapsed = time.monotonic() - started_at
            if elapsed > self.config.job_timeout_seconds:
                raise RemoteMasteringError(
                    "AI Mastering job timed out",
                    f"No completed result after {int(self.config.job_timeout_seconds)} seconds.",
                )
            mastering = self._json_request("GET", f"/masterings/{mastering_id}")
            status = str(mastering.get("status", ""))
            progression = mastering.get("progression")
            if status == "succeeded":
                self._notify(progress_callback, "AI Mastering cloud job complete", 82)
                return mastering
            if status in {"failed", "canceled"}:
                details = mastering.get("failure_reason") or json.dumps(mastering)
                raise RemoteMasteringError(f"AI Mastering job {status}", str(details))
            percent = 60
            if isinstance(progression, int | float):
                percent = 60 + int(max(0.0, min(float(progression), 1.0)) * 20)
            self._notify(
                progress_callback,
                f"AI Mastering cloud job {status or 'processing'} ({int(elapsed)}s)",
                percent,
            )
            self._sleep_with_cancel(cancel_callback)

    def _download_audio(self, audio_id: int, output_path: Path) -> None:
        token_response = self._json_request("GET", f"/audios/{audio_id}/download_token")
        download_url = token_response.get("download_url")
        if isinstance(download_url, str) and download_url:
            data = self._raw_request("GET", download_url, absolute=True)
        else:
            download_token = token_response.get("download_token")
            if not isinstance(download_token, str) or not download_token:
                raise RemoteMasteringError("AI Mastering did not return a download token", json.dumps(token_response))
            data = self._raw_request("GET", f"/audios/download_by_token?{urlencode({'download_token': download_token})}")
        output_path.write_bytes(data)

    def _json_request(self, method: str, path: str) -> dict[str, object]:
        data = self._raw_request(method, path)
        try:
            payload = json.loads(data.decode("utf-8"))
        except json.JSONDecodeError as exc:
            raise RemoteMasteringError("AI Mastering returned invalid JSON", str(exc)) from exc
        if not isinstance(payload, dict):
            raise RemoteMasteringError("AI Mastering returned an unexpected response", str(payload))
        return payload

    def _multipart_json(self, method: str, path: str, fields: dict[str, str], files: dict[str, Path]) -> dict[str, object]:
        boundary = f"----optimaster-{uuid.uuid4().hex}"
        body = self._encode_multipart(fields, files, boundary)
        headers = {"Content-Type": f"multipart/form-data; boundary={boundary}"}
        data = self._raw_request(method, path, body=body, headers=headers)
        try:
            payload = json.loads(data.decode("utf-8"))
        except json.JSONDecodeError as exc:
            raise RemoteMasteringError("AI Mastering returned invalid JSON", str(exc)) from exc
        if not isinstance(payload, dict):
            raise RemoteMasteringError("AI Mastering returned an unexpected response", str(payload))
        return payload

    def _raw_request(
        self,
        method: str,
        path_or_url: str,
        body: bytes | None = None,
        headers: dict[str, str] | None = None,
        absolute: bool = False,
    ) -> bytes:
        url = path_or_url if absolute else f"{self.config.base_url}{path_or_url}"
        request_headers = {"Authorization": self._authorization}
        if headers:
            request_headers.update(headers)
        request = Request(url, data=body, headers=request_headers, method=method)
        try:
            with urlopen(request, timeout=self.config.timeout_seconds) as response:
                return response.read()
        except HTTPError as exc:
            details = exc.read().decode("utf-8", errors="replace")
            raise RemoteMasteringError(f"AI Mastering HTTP {exc.code}", details) from exc
        except URLError as exc:
            raise RemoteMasteringError("Could not reach AI Mastering", str(exc.reason)) from exc
        except TimeoutError as exc:
            raise RemoteMasteringError("AI Mastering request timed out", str(exc)) from exc

    def _encode_multipart(self, fields: dict[str, str], files: dict[str, Path], boundary: str) -> bytes:
        chunks: list[bytes] = []
        for name, value in fields.items():
            chunks.extend(
                [
                    f"--{boundary}\r\n".encode("utf-8"),
                    f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode("utf-8"),
                    f"{value}\r\n".encode("utf-8"),
                ]
            )
        for name, path in files.items():
            content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
            chunks.extend(
                [
                    f"--{boundary}\r\n".encode("utf-8"),
                    (
                        f'Content-Disposition: form-data; name="{name}"; '
                        f'filename="{path.name}"\r\n'
                    ).encode("utf-8"),
                    f"Content-Type: {content_type}\r\n\r\n".encode("utf-8"),
                    path.read_bytes(),
                    b"\r\n",
                ]
            )
        chunks.append(f"--{boundary}--\r\n".encode("utf-8"))
        return b"".join(chunks)

    @staticmethod
    def _required_id(payload: dict[str, object], label: str) -> int:
        value = payload.get("id")
        if not isinstance(value, int):
            raise RemoteMasteringError(f"AI Mastering returned no {label} id", json.dumps(payload))
        return value

    def _sleep_with_cancel(self, cancel_callback: CancelCallback | None) -> None:
        remaining = max(0.5, self.config.poll_interval_seconds)
        while remaining > 0:
            self._raise_if_cancelled(cancel_callback)
            step = min(0.25, remaining)
            time.sleep(step)
            remaining -= step

    @staticmethod
    def _notify(progress_callback: ProgressCallback | None, message: str, percent: int) -> None:
        if progress_callback is not None:
            progress_callback(message, max(0, min(percent, 100)))

    @staticmethod
    def _raise_if_cancelled(cancel_callback: CancelCallback | None) -> None:
        if cancel_callback is not None and cancel_callback():
            raise OperationCancelledError()
