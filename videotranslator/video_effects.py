"""The 80s monitor look on the video: an mpv GLSL shader for the CRT skins.

Barrel curvature, a dark scanline every two output pixels, a vignette and a
faint phosphor tint (green or amber). It runs on the GPU inside mpv, after
scaling and before the subtitles and the live captions, which stay sharp.
Video outputs without shader support (the software fallback) ignore it.
The shader text is written once to a cache file, because mpv loads shaders
from paths.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

# Skin -> phosphor tint (r, g, b multipliers).
CRT_TINTS: dict[str, tuple[float, float, float]] = {
    "crt": (0.92, 1.04, 0.92),
    "crt_amber": (1.04, 0.97, 0.86),
}

_SHADER = """//!HOOK OUTPUT
//!BIND HOOKED
//!DESC VideoTranslatorAI CRT: scanlines, vignette, slight curvature, phosphor tint

vec4 hook() {{
    vec2 uv = HOOKED_pos;
    vec2 c = uv * 2.0 - 1.0;
    float r2 = dot(c, c);
    c *= 1.0 + 0.045 * r2;
    uv = c * 0.5 + 0.5;
    if (uv.x < 0.0 || uv.x > 1.0 || uv.y < 0.0 || uv.y > 1.0)
        return vec4(0.0, 0.0, 0.0, 1.0);
    vec4 col = HOOKED_tex(uv);
    col.rgb *= 0.82 + 0.18 * sin(uv.y * HOOKED_size.y * 3.14159265);
    col.rgb *= 1.0 - 0.40 * r2;
    col.rgb *= vec3({r:.2f}, {g:.2f}, {b:.2f});
    return col;
}}
"""


def crt_shader_source(tint: tuple[float, float, float]) -> str:
    r, g, b = tint
    return _SHADER.format(r=r, g=g, b=b)


def shader_for_theme(theme: str, cache_dir: Path | None = None) -> str | None:
    """Path of the shader for ``theme`` (written if needed), or None when the
    theme has no video effect or the file cannot be written."""
    tint = CRT_TINTS.get(theme)
    if tint is None:
        return None
    folder = Path(cache_dir) if cache_dir else Path(tempfile.gettempdir()) / "VideoTranslatorAI"
    path = folder / f"{theme}.glsl"
    source = crt_shader_source(tint)
    try:
        if not path.is_file() or path.read_text(encoding="utf-8") != source:
            folder.mkdir(parents=True, exist_ok=True)
            part = path.with_name(path.name + ".part")
            part.write_text(source, encoding="utf-8")
            part.replace(path)
    except OSError:
        return None
    return str(path)
