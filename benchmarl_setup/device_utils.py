from __future__ import annotations

import re

import torch


_DEVICE_PATTERN = re.compile(r"^(auto|cpu|cuda(?::\d+)?)$")


def normalize_device_string(raw: str) -> str:
    value = raw.strip().lower()
    if not value:
        raise ValueError("Device value cannot be empty.")
    if _DEVICE_PATTERN.fullmatch(value) is None:
        raise ValueError(
            "Unsupported device value. Use one of: auto, cpu, cuda, cuda:<index>."
        )
    return value


def parse_device_list(raw: str) -> list[str]:
    values = [normalize_device_string(item) for item in raw.split(",") if item.strip()]
    if not values:
        raise ValueError("At least one device must be provided.")
    return values


def device_label(device: str) -> str:
    normalized = normalize_device_string(device)
    return normalized.replace(":", "_")


def resolve_device(requested_device: str, allow_cpu_fallback: bool) -> tuple[str, str]:
    requested = normalize_device_string(requested_device)

    if requested == "auto":
        if torch.cuda.is_available():
            return "cuda", "auto-selected CUDA because torch.cuda.is_available() is True"
        return "cpu", "auto-selected CPU because CUDA is unavailable"

    if requested == "cpu":
        return "cpu", "explicit CPU request"

    if torch.cuda.is_available():
        if ":" in requested:
            index = int(requested.split(":", 1)[1])
            if index >= torch.cuda.device_count():
                if allow_cpu_fallback:
                    return (
                        "cpu",
                        "requested CUDA index is out of range; using CPU fallback",
                    )
                raise ValueError(
                    f"Requested CUDA device index {index} is out of range for this machine."
                )
        return requested, "explicit CUDA request"

    if allow_cpu_fallback:
        return "cpu", "CUDA requested but unavailable; using CPU fallback"

    raise ValueError(
        "CUDA was requested but is not available. Install CUDA-enabled PyTorch or use --device cpu."
    )