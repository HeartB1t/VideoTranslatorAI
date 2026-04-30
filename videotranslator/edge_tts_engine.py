"""Edge-TTS generation helpers."""

from __future__ import annotations

import asyncio
import os
from collections.abc import Awaitable, Callable
from typing import Any


LogCallback = Callable[..., None]
SleepCallback = Callable[[float], Awaitable[Any]]
CommunicateFactory = Callable[..., Any]


async def tts_segment(
    text: str,
    voice: str,
    out_path: str,
    *,
    rate: str = "+0%",
    retries: int = 5,
    communicate_factory: CommunicateFactory | None = None,
    sleep: SleepCallback = asyncio.sleep,
    log: LogCallback = print,
) -> None:
    """Generate one Edge-TTS segment with exponential-backoff retries."""
    if communicate_factory is None:
        import edge_tts  # type: ignore

        communicate_factory = edge_tts.Communicate

    for attempt in range(retries):
        try:
            comm = communicate_factory(text, voice, rate=rate)
            await comm.save(out_path)
            return
        except Exception as exc:
            if attempt < retries - 1:
                wait = 2**attempt
                log(
                    f"     ! TTS retry {attempt + 1} ({exc.__class__.__name__}) "
                    f"in {wait}s...",
                    flush=True,
                )
                await sleep(wait)
            else:
                log(
                    f"     ! TTS failed: {text[:40]!r} "
                    f"({exc.__class__.__name__}: {exc})",
                    flush=True,
                )


async def tts_all(
    segments: list[dict],
    voice: str,
    tmp_dir: str,
    rate: str,
    *,
    max_concurrent: int = 4,
    segment_runner: Callable[..., Awaitable[None]] = tts_segment,
    exists: Callable[[str], bool] = os.path.exists,
    log: LogCallback = print,
) -> list[str]:
    """Generate all Edge-TTS segments with bounded HTTP concurrency."""
    # Edge-TTS is HTTP-only. A small semaphore avoids service-side 429/timeouts
    # without materially reducing throughput.
    total = len(segments)
    files = [os.path.join(tmp_dir, f"seg_{i:04d}.mp3") for i in range(total)]
    sem = asyncio.Semaphore(max(1, max_concurrent))
    done_counter = {"n": 0, "failed": 0}

    async def run_one(i: int) -> None:
        text = (segments[i].get("text_tgt") or "").strip()
        if not text:
            return
        async with sem:
            await segment_runner(text, voice, files[i], rate=rate)
        if not exists(files[i]):
            done_counter["failed"] += 1
        done_counter["n"] += 1
        if done_counter["n"] % 10 == 0 or done_counter["n"] == total:
            log(f"     {done_counter['n']}/{total}...", end="\r", flush=True)

    await asyncio.gather(*(run_one(i) for i in range(total)))
    if done_counter["failed"]:
        log(
            f"     ! Warning: {done_counter['failed']}/{total} TTS segments "
            f"failed and will be silent.",
            flush=True,
        )
    return files


def generate_tts(
    segments: list[dict],
    voice: str,
    tmp_dir: str,
    rate: str = "+0%",
    *,
    all_runner: Callable[..., Awaitable[list[str]]] = tts_all,
    run: Callable[[Awaitable[list[str]]], list[str]] = asyncio.run,
    log: LogCallback = print,
) -> list[str]:
    """Generate Edge-TTS files for translated segments."""
    log(f"[5/6] Generating TTS (voice={voice}, rate={rate})...", flush=True)
    files = run(all_runner(segments, voice, tmp_dir, rate))
    log("     → TTS done                   ", flush=True)
    return files
