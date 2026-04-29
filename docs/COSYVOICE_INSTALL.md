# CosyVoice 3 — Manual Setup (Linux)

The CosyVoice GUI checkbox in VideoTranslatorAI tries to `pip install
cosyvoice` automatically, but this PyPI package (`cosyvoice 0.0.8`) is a
community wrapper by Lucas Jin that has been abandoned and **fails to
build on Python ≥ 3.12** (`KeyError: '__version__'` in `setup.py`).

The upstream maintainer FunAudioLLM publishes CosyVoice as a **clone-only**
project that expects a dedicated **conda environment with Python 3.10**.
This document describes the two install paths.

If your system Python is **3.10 or 3.11**, the in-app auto-install may
work — try the GUI checkbox first. If your system Python is **3.12 or
newer** (Kali / Debian testing / Arch / Ubuntu 24.04 +) the GUI will
fail-fast with an explanatory log message and you need to follow Path B
below to actually try CosyVoice.

The pipeline always falls back to **XTTS v2** when CosyVoice is not
installed, so following this guide is optional — XTTS already produces
production-quality dubbing.

---

## Path A — Quick attempt (Python 3.10 / 3.11)

Tick the *Voice Cloning Pro* checkbox in the GUI and accept the install
prompt. The pipeline runs:

```sh
python -m pip install --break-system-packages cosyvoice
```

If this completes without error, the model (~1.7 GB) will download from
ModelScope on the first synthesis run. If it fails, switch to Path B.

---

## Path B — Conda environment (recommended on Python 3.12+)

This sets up an isolated environment matching the upstream maintainer's
recommendation. It does **not** affect your system Python.

### 1. Install conda (one-off)

```sh
# miniconda is the lightest installer
wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh
bash Miniconda3-latest-Linux-x86_64.sh
# accept defaults; relaunch shell
```

### 2. Clone CosyVoice with submodules

```sh
mkdir -p ~/.local/share/cosyvoice && cd ~/.local/share/cosyvoice
git clone --recursive https://github.com/FunAudioLLM/CosyVoice.git
cd CosyVoice
# if the submodule clone fails due to network, retry:
git submodule update --init --recursive
```

### 3. Create the conda environment

```sh
conda create -n cosyvoice -y python=3.10
conda activate cosyvoice
conda install -y -c conda-forge pynini==2.1.5
pip install -r requirements.txt --extra-index-url https://download.pytorch.org/whl/cu124
```

### 4. Verify the install

```sh
conda activate cosyvoice
python -c "import cosyvoice; print('CosyVoice imported:', cosyvoice.__file__)"
```

If the import succeeds, CosyVoice is ready inside the conda env.

### 5. Run VideoTranslatorAI from inside the env

```sh
conda activate cosyvoice
cd ~/Scrivania/VideoTranslatorAI
python video_translator_gui.py
```

The GUI launches inside the conda env, the *Voice Cloning Pro* checkbox
will detect the working CosyVoice import, and the pipeline can use it.

You only need to `conda activate cosyvoice` before launching the GUI.
Without that activation the system Python (3.12 / 3.13) is used and
CosyVoice falls back to XTTS automatically.

---

## Troubleshooting

| Symptom | Cause | Fix |
| --- | --- | --- |
| `KeyError: '__version__'` | PyPI wrapper rotto, Python ≥ 3.12 | Path B (conda env Python 3.10) |
| `ImportError: pynini` | conda-forge non installato | `conda install -y -c conda-forge pynini==2.1.5` |
| `tensorrt-cu12 build error` | Wheel non disponibile per la tua CUDA | rimuovi `tensorrt-cu12` da `requirements.txt`, gira senza accelerazione TRT |
| Model download fails ModelScope | firewall / area geografica | il wrapper cade automaticamente su HuggingFace `iic/CosyVoice-300M-Instruct` |
| OOM su RTX 3090 con XTTS attivo | GPU saturata | esegui CosyVoice senza Wav2Lip / Demucs in parallelo |

---

## Why CosyVoice if XTTS already works?

CosyVoice 3 (December 2025) advantages:

- **Apache 2.0** license (XTTS v2 uses CPML, restrictive on commercial use)
- **9 native languages** including Italian, with cross-lingual zero-shot
  cloning quality slightly above XTTS on long-form
- **Pronunciation inpainting** (Chinese pinyin + English CMU phonemes)
  for explicit pronunciation control on technical terms — relevant if
  you want to force the English pronunciation of `API`, `Docker`,
  `Ctrl+C` instead of the Italian-accented output XTTS produces
- **Streaming inference** with ~150 ms latency

If those are not requirements for you, **XTTS v2 is a fine default** and
this whole setup is optional.

---

## Reverting to XTTS

Untick the *Voice Cloning Pro* checkbox in the GUI. The pipeline goes
back to XTTS v2 immediately, no other change needed. The conda env can
be left in place or removed with `conda env remove -n cosyvoice`.
