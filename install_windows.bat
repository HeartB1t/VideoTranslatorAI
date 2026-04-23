@echo off
:: Use UTF-8 codepage for non-ASCII paths/usernames
chcp 65001 >nul
setlocal enabledelayedexpansion
title Video Translator AI - Installer
color 0A

:: -- Check administrator privileges -------------------------------------------
net session >nul 2>&1
if not errorlevel 1 goto admin_ok
color 0C
echo.
echo  ============================================
echo    ERROR: Run as Administrator!
echo  ============================================
echo.
echo  Right-click on install_windows.bat and select
echo  "Run as administrator", then try again.
echo.
pause
exit /b 1
:admin_ok

echo.
echo  ============================================
echo    Video Translator AI - Windows Installer
echo  ============================================
echo.

:: -- Preflight checks (architecture, disk space, internet) ---------------
:: Can be bypassed for testing with: set VTAI_SKIP_PREFLIGHT=1

:: CPU architecture (x64 required for Python/PyTorch CUDA/dlib/ffmpeg wheels)
if /i "%VTAI_SKIP_PREFLIGHT%"=="1" goto arch_ok
set "VTAI_ARCH=%PROCESSOR_ARCHITECTURE%"
if defined PROCESSOR_ARCHITEW6432 set "VTAI_ARCH=%PROCESSOR_ARCHITEW6432%"
if /i "%VTAI_ARCH%"=="AMD64" goto arch_ok
color 0C
echo.
echo  ============================================
echo    ERROR: Unsupported architecture (%VTAI_ARCH%)
echo  ============================================
echo.
echo  This installer requires Windows x64 (AMD64).
echo.
echo  ARM64 and 32-bit x86 are not supported: the downloaded
echo  Python, PyTorch CUDA, dlib and ffmpeg binaries are x64 only.
echo.
pause
exit /b 1
:arch_ok

:: Free disk space on install drive (at least 20 GB required)
if /i "%VTAI_SKIP_PREFLIGHT%"=="1" goto disk_ok
set "INSTALL_DRIVE=%ProgramFiles:~0,1%"
set "FREE_GB=0"
for /f %%i in ('powershell -NoProfile -Command "[math]::Floor((Get-PSDrive '%INSTALL_DRIVE%').Free/1GB)"') do set "FREE_GB=%%i"
if %FREE_GB% GEQ 20 goto disk_ok
color 0C
echo.
echo  ============================================
echo    ERROR: Insufficient disk space
echo  ============================================
echo.
echo  Found %FREE_GB% GB free on %INSTALL_DRIVE%:, but at least 20 GB is required.
echo.
echo  The full install (PyTorch CUDA, Whisper large-v3, XTTS, Wav2Lip) needs ~15 GB.
echo.
pause
exit /b 1
:disk_ok

:: Internet connection (HEAD to github.com, 5s timeout)
if /i "%VTAI_SKIP_PREFLIGHT%"=="1" goto net_ok
echo  [*] Checking Internet connection...
powershell -NoProfile -Command "try { [Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]::Tls12; $r=[Net.WebRequest]::Create('https://github.com'); $r.Method='HEAD'; $r.Timeout=5000; $r.GetResponse().Close(); exit 0 } catch { exit 1 }" >nul 2>&1
if not errorlevel 1 goto net_ok
color 0C
echo.
echo  ============================================
echo    ERROR: No Internet connection
echo  ============================================
echo.
echo  Cannot reach https://github.com (HTTPS/443).
echo.
echo  The installer needs to download Python, PyTorch, ffmpeg, Git and AI models (several GB).
echo.
echo  Check network / proxy / firewall and try again.
echo.
pause
exit /b 1
:net_ok

:: -- Installation directory (system-wide, multi-user) --------------------
:: Tutti gli asset in %ProgramFiles% → accessibili a qualsiasi utente Windows
set "INSTALL_DIR=%ProgramFiles%\VideoTranslatorAI"
set "FFMPEG_DIR=%INSTALL_DIR%\ffmpeg"
set "SCRIPT_DIR=%~dp0"

:: -- Legacy cleanup: rimuovi vecchia install per-utente (versioni pre-multiuser)
set "LEGACY_DIR=%USERPROFILE%\VideoTranslatorAI"
set "LEGACY_WAV2LIP=%USERPROFILE%\.local\share\wav2lip"
set "LEGACY_SHORTCUT=%USERPROFILE%\Desktop\Video Translator AI.lnk"
if exist "%LEGACY_DIR%" (
    echo  [*] Rimozione vecchia installazione per-utente: %LEGACY_DIR%
    rmdir /S /Q "%LEGACY_DIR%" 2>nul
)
if exist "%LEGACY_WAV2LIP%" (
    echo  [*] Rimozione vecchi modelli Wav2Lip per-utente...
    rmdir /S /Q "%LEGACY_WAV2LIP%" 2>nul
)
if exist "%LEGACY_SHORTCUT%" del /Q "%LEGACY_SHORTCUT%" 2>nul

:: -- 1. Check / Auto-install Python ---------------------------------------
echo [1/5] Checking Python...
python --version >nul 2>&1
if not errorlevel 1 goto python_found

REM Python 3.11 is the recommended target:
REM   - dlib wheels (z-mahmud22) cover 3.9-3.13
REM   - coqui-tts fork (maintained) is installed for all versions (see below)
echo  [!] Python not found. Downloading and installing Python 3.11 silently...
powershell -Command ^
    "$url = 'https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe';" ^
    "$out = $env:TEMP + '\python_installer.exe';" ^
    "Write-Host '     Downloading Python 3.11.9...';" ^
    "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12;" ^
    "Invoke-WebRequest -Uri $url -OutFile $out -UseBasicParsing;" ^
    "Write-Host '     Installing silently (this may take a minute)...';" ^
    "Start-Process -FilePath $out -ArgumentList '/quiet InstallAllUsers=1 PrependPath=1 Include_test=0 Include_doc=0' -Wait;" ^
    "Remove-Item $out -Force;" ^
    "Write-Host '  [+] Python 3.11 installed successfully.'"

if errorlevel 1 (
    echo  [!] Auto-install failed. Download manually from:
    echo      https://www.python.org/downloads/
    echo      Check "Add Python to PATH" during installation, then re-run this bat.
    pause
    exit /b 1
)

:: Reload PATH so python is available in current session
:: Use a temp file to avoid the 8191-char buffer limit of for /f on long PATHs
powershell -NoProfile -Command "[Environment]::GetEnvironmentVariable('PATH','Machine') + ';' + [Environment]::GetEnvironmentVariable('PATH','User') | Out-File -Encoding UTF8 -Width 32768 -FilePath $env:TEMP\vtai_path.txt"
set "PATH="
for /f "usebackq delims=" %%i in ("%TEMP%\vtai_path.txt") do set "PATH=!PATH!%%i"
del /Q "%TEMP%\vtai_path.txt" >nul 2>&1

:python_found
for /f "tokens=*" %%i in ('python --version 2^>^&1') do set "PY_VER=%%i"
echo  [+] Found: %PY_VER%

:: Require Python 3.9+
python -c "import sys; exit(0 if sys.version_info >= (3,9) else 1)" >nul 2>&1
if errorlevel 1 (
    echo  [!] Python 3.9 or higher is required.
    pause
    exit /b 1
)

:: -- 2. Create installation folder -----------------------------------------
echo.
echo [2/5] Preparing installation folder...
if not exist "%INSTALL_DIR%" mkdir "%INSTALL_DIR%"
echo  [+] Folder: %INSTALL_DIR%

:: Copy Python script to installation folder (single-file pipeline since v1.0)
echo  [*] Copying script...
copy /Y "%SCRIPT_DIR%video_translator_gui.py" "%INSTALL_DIR%\video_translator_gui.py" >nul
if errorlevel 1 (
    echo  [!] Error copying script. Make sure video_translator_gui.py is in the same folder as this .bat
    pause
    exit /b 1
)
echo  [+] Script copied.

:: -- 3. Install Python dependencies ----------------------------------------
echo.
echo [3/5] Installing Python dependencies...
echo  [*] Upgrading pip...
python -m pip install --upgrade pip --quiet

set PACKAGES=faster-whisper demucs soundfile edge-tts deep-translator pydub yt-dlp pyloudnorm sentencepiece sacremoses "pyannote.audio<4.0" torchcodec

:: Python 3.13+ requires audioop-lts
python -c "import sys; exit(0 if sys.version_info >= (3,13) else 1)" >nul 2>&1
if not errorlevel 1 (
    set PACKAGES=%PACKAGES% audioop-lts
)

:: Install PyTorch with CUDA 12.4 (compatible with modern NVIDIA drivers)
:: torchvision pinned to 0.21.0 (matched to torch 2.6.0) to prevent transitive
:: deps (basicsr/facexlib) from pulling torchvision 0.26+ which requires torch 2.11.
echo  [*] Installing PyTorch cu124 + torchaudio + torchvision...
python -m pip install "torch==2.6.0" "torchaudio==2.6.0" "torchvision==0.21.0" --quiet ^
  --index-url https://download.pytorch.org/whl/cu124
if errorlevel 1 (
    echo  [!] PyTorch cu124 failed, trying CPU version...
    python -m pip install "torch==2.6.0" "torchaudio==2.6.0" "torchvision==0.21.0" --quiet
)

:: Install ctranslate2 explicitly first (faster-whisper dependency, Windows-sensitive)
echo  [*] Installing ctranslate2...
python -m pip install ctranslate2 --quiet

echo  [*] Installing packages: %PACKAGES%
python -m pip install %PACKAGES% --quiet
if errorlevel 1 (
    echo  [!] Error installing Python packages.
    pause
    exit /b 1
)

:: Verify PyTorch CUDA wasn't downgraded by a dependency (e.g. pyannote.audio)
python -c "import torch,sys; sys.exit(0 if '+cu' in torch.__version__ else 1)" >nul 2>&1
if errorlevel 1 (
    echo  [!] PyTorch CUDA was downgraded by a dependency. Reinstalling cu124...
    python -m pip install --upgrade --force-reinstall --no-deps "torch==2.6.0" "torchaudio==2.6.0" "torchvision==0.21.0" --index-url https://download.pytorch.org/whl/cu124 --quiet
    if errorlevel 1 echo  [!] PyTorch cu124 reinstall failed - GPU acceleration may be unavailable.
)

:: Pin transformers<5.1 (5.x rimuove isin_mps_friendly; coqui-tts issue #558 con 5.1+)
echo  [*] Installing transformers ^(^>=4.40.0,^<5.1^)...
python -m pip install "transformers>=4.40.0,<5.1" --quiet
if errorlevel 1 (
    echo  [!] transformers install failed.
    pause
    exit /b 1
)

:: Install Coqui TTS separately (requires C++ Build Tools on Windows)
python -m pip install Cython setuptools wheel --quiet
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8

:: Helper: activate MSVC compiler environment if vcvarsall.bat is available
call :find_vcvarsall

:: Fork coqui-tts (Idiap) — mantenuto, wheel prebuildati Py 3.9+, evita il
:: setup.py rotto del pacchetto originale TTS su Windows.
echo  [*] Installing coqui-tts fork (voice cloning)...
:: Attempt 1: wheel prebuildato, niente build isolation
python -m pip install coqui-tts "transformers<5.1" --quiet 2>nul
if not errorlevel 1 goto tts_ok

:: Attempt 2: no-build-isolation (se servisse compilazione locale)
python -m pip install coqui-tts "transformers<5.1" --no-build-isolation --quiet 2>nul
if not errorlevel 1 goto tts_ok
goto tts_need_buildtools

:tts_need_buildtools
:: Attempt 3: auto-install VS C++ Build Tools, then activate env and retry
echo  [*] VS C++ Build Tools not found - downloading and installing silently...
echo      (this may take 5-10 minutes, please wait)
powershell -Command ^
    "$url = 'https://aka.ms/vs/17/release/vs_BuildTools.exe';" ^
    "$out = $env:TEMP + '\vs_BuildTools.exe';" ^
    "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12;" ^
    "Invoke-WebRequest -Uri $url -OutFile $out -UseBasicParsing;" ^
    "Write-Host '     Installing VS C++ Build Tools (silent)...';" ^
    "Start-Process -FilePath $out -ArgumentList '--quiet --wait --norestart --nocache --installPath C:\BuildTools --add Microsoft.VisualStudio.Workload.VCTools --includeRecommended' -Wait;" ^
    "Remove-Item $out -Force;" ^
    "Write-Host '  [+] VS Build Tools installed.'"

if errorlevel 1 (
    echo  [!] VS Build Tools auto-install failed. Voice cloning skipped.
    goto tts_failed
)

:: Activate MSVC compiler environment (makes cl.exe visible in current session)
call :find_vcvarsall

:: Retry coqui-tts with compiler now active
python -m pip install coqui-tts "transformers<5.1" --no-build-isolation --quiet 2>nul
if not errorlevel 1 goto tts_ok

:tts_failed
echo.
echo  +------------------------------------------------------+
echo  ^|  Voice Cloning (XTTS v2) could not be installed.    ^|
echo  ^|  Everything else works normally.                     ^|
echo  ^|                                                      ^|
echo  ^|  To enable voice cloning manually:                   ^|
echo  ^|  1. Install Visual Studio Build Tools 2022:          ^|
echo  ^|     https://aka.ms/vs/17/release/vs_BuildTools.exe   ^|
echo  ^|     Select: "Desktop development with C++"           ^|
echo  ^|  2. Reopen this terminal and run:                    ^|
echo  ^|     pip install coqui-tts "transformers<5.1"            ^|
echo  +------------------------------------------------------+
echo.
goto tts_end

:tts_ok
echo  [+] Coqui TTS installed successfully.

:tts_end

:: -- 3b. Install Wav2Lip dependencies (Lip Sync) --------------------------
echo.
echo  [*] Installing Wav2Lip dependencies (basicsr, facexlib, dlib)...

:: Detect Python major.minor version for dlib wheel selection
for /f "tokens=*" %%i in ('python -c "import sys; print(f'{sys.version_info.major}{sys.version_info.minor}')"') do set "PY_TAG=%%i"
echo  [*] Python tag detected: cp%PY_TAG%

set "DLIB_WHEEL_URL="
if "%PY_TAG%"=="39"  set "DLIB_WHEEL_URL=https://github.com/z-mahmud22/Dlib_Windows_Python3.x/raw/main/dlib-19.22.99-cp39-cp39-win_amd64.whl"
if "%PY_TAG%"=="310" set "DLIB_WHEEL_URL=https://github.com/z-mahmud22/Dlib_Windows_Python3.x/raw/main/dlib-19.22.99-cp310-cp310-win_amd64.whl"
if "%PY_TAG%"=="311" set "DLIB_WHEEL_URL=https://github.com/z-mahmud22/Dlib_Windows_Python3.x/raw/main/dlib-19.24.1-cp311-cp311-win_amd64.whl"
if "%PY_TAG%"=="312" set "DLIB_WHEEL_URL=https://github.com/z-mahmud22/Dlib_Windows_Python3.x/raw/main/dlib-19.24.99-cp312-cp312-win_amd64.whl"
if "%PY_TAG%"=="313" set "DLIB_WHEEL_URL=https://github.com/z-mahmud22/Dlib_Windows_Python3.x/raw/main/dlib-19.24.99-cp313-cp313-win_amd64.whl"

python -c "import dlib" >nul 2>&1
if not errorlevel 1 (
    echo  [+] dlib already installed.
    goto dlib_done
)

if not defined DLIB_WHEEL_URL (
    echo  [!] No pre-built dlib wheel for cp%PY_TAG%. Lip Sync may not work.
    goto dlib_done
)

echo  [*] Installing dlib wheel for cp%PY_TAG%...
python -m pip install "%DLIB_WHEEL_URL%" --quiet
if errorlevel 1 (
    echo  [!] dlib wheel install failed. Lip Sync may not work.
) else (
    echo  [+] dlib installed from pre-built wheel.
)

:dlib_done
python -m pip install basicsr facexlib --quiet
if errorlevel 1 (
    echo  [!] basicsr/facexlib install failed. Lip Sync may not work.
) else (
    echo  [+] basicsr and facexlib installed.
)

:: Download Wav2Lip GAN model (~416MB) and clone repo (system-wide)
set "WAV2LIP_DIR=%INSTALL_DIR%\wav2lip"
set "WAV2LIP_MODEL=%WAV2LIP_DIR%\wav2lip_gan.pth"
set "WAV2LIP_REPO=%WAV2LIP_DIR%\Wav2Lip"

if not exist "%WAV2LIP_DIR%" mkdir "%WAV2LIP_DIR%"

if exist "%WAV2LIP_REPO%\inference.py" goto wav2lip_repo_done

:: Check for git; auto-install Git for Windows if missing
where git >nul 2>&1
if not errorlevel 1 goto wav2lip_clone

echo  [!] git not found. Downloading and installing Git for Windows silently...
powershell -Command ^
    "$url = 'https://github.com/git-for-windows/git/releases/download/v2.47.1.windows.1/Git-2.47.1-64-bit.exe';" ^
    "$out = $env:TEMP + '\git_installer.exe';" ^
    "Write-Host '     Downloading Git for Windows 2.47.1...';" ^
    "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12;" ^
    "Invoke-WebRequest -Uri $url -OutFile $out -UseBasicParsing;" ^
    "Write-Host '     Installing silently (this may take a minute)...';" ^
    "Start-Process -FilePath $out -ArgumentList '/VERYSILENT','/NORESTART','/NOCANCEL','/SP-','/SUPPRESSMSGBOXES','/COMPONENTS=icons,ext\reg\shellhere,assoc,assoc_sh' -Wait;" ^
    "Remove-Item $out -Force;" ^
    "Write-Host '  [+] Git for Windows installed.'"
if errorlevel 1 (
    echo  [!] Git auto-install failed. Install manually from https://git-scm.com/download/win
    goto wav2lip_repo_done
)

:: Reload PATH so git is visible in the current session
:: Use a temp file to avoid the 8191-char buffer limit of for /f on long PATHs
powershell -NoProfile -Command "[Environment]::GetEnvironmentVariable('PATH','Machine') + ';' + [Environment]::GetEnvironmentVariable('PATH','User') | Out-File -Encoding UTF8 -Width 32768 -FilePath $env:TEMP\vtai_path.txt"
set "PATH="
for /f "usebackq delims=" %%i in ("%TEMP%\vtai_path.txt") do set "PATH=!PATH!%%i"
del /Q "%TEMP%\vtai_path.txt" >nul 2>&1

:: Give the installer a moment to finalize registry/PATH writes
timeout /t 2 /nobreak >nul

:: Probe common install locations (system-wide + per-user) and prepend to PATH
if exist "%ProgramFiles%\Git\cmd\git.exe" set "PATH=%ProgramFiles%\Git\cmd;%PATH%"
if exist "%ProgramFiles(x86)%\Git\cmd\git.exe" set "PATH=%ProgramFiles(x86)%\Git\cmd;%PATH%"
if exist "%LOCALAPPDATA%\Programs\Git\cmd\git.exe" set "PATH=%LOCALAPPDATA%\Programs\Git\cmd;%PATH%"

where git >nul 2>&1
if errorlevel 1 (
    echo  [!] git still not found after install. Lip Sync disabled.
    goto wav2lip_repo_done
)

:wav2lip_clone
echo  [*] Cloning Wav2Lip repo...
git clone --depth 1 https://github.com/Rudrabha/Wav2Lip.git "%WAV2LIP_REPO%"
if errorlevel 1 echo  [!] Wav2Lip clone failed. Lip Sync disabled.

:wav2lip_repo_done

if exist "%WAV2LIP_MODEL%" (
    echo  [+] Wav2Lip GAN model already present.
    goto wav2lip_model_done
)

echo  [*] Downloading Wav2Lip GAN model ^(~416MB^)...

:wav2lip_model_try1
echo  [*] Trying primary mirror (Non-playing-Character)...
powershell -Command ^
    "try {" ^
    "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12;" ^
    "Invoke-WebRequest -Uri 'https://huggingface.co/Non-playing-Character/Wave2lip/resolve/main/wav2lip_gan.pth' -OutFile '%WAV2LIP_MODEL%' -UseBasicParsing -ErrorAction Stop;" ^
    "exit 0" ^
    "} catch { exit 1 }"
if errorlevel 1 goto wav2lip_model_try1_fail
powershell -NoProfile -Command "if ((Get-Item '%WAV2LIP_MODEL%').Length -lt 100MB) { exit 1 } else { exit 0 }"
if not errorlevel 1 goto wav2lip_model_verify
:wav2lip_model_try1_fail
echo  [!] Primary mirror failed.
if exist "%WAV2LIP_MODEL%" del /Q "%WAV2LIP_MODEL%" >nul 2>&1

:wav2lip_model_try2
echo  [*] Trying fallback mirror 1 (Nekochu)...
powershell -Command ^
    "try {" ^
    "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12;" ^
    "Invoke-WebRequest -Uri 'https://huggingface.co/Nekochu/Wav2Lip/resolve/main/wav2lip_gan.pth' -OutFile '%WAV2LIP_MODEL%' -UseBasicParsing -ErrorAction Stop;" ^
    "exit 0" ^
    "} catch { exit 1 }"
if errorlevel 1 goto wav2lip_model_try2_fail
powershell -NoProfile -Command "if ((Get-Item '%WAV2LIP_MODEL%').Length -lt 100MB) { exit 1 } else { exit 0 }"
if not errorlevel 1 goto wav2lip_model_verify
:wav2lip_model_try2_fail
echo  [!] Fallback mirror 1 failed.
if exist "%WAV2LIP_MODEL%" del /Q "%WAV2LIP_MODEL%" >nul 2>&1

:wav2lip_model_try3
echo  [*] Trying fallback mirror 2 (rippertnt)...
powershell -Command ^
    "try {" ^
    "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12;" ^
    "Invoke-WebRequest -Uri 'https://huggingface.co/rippertnt/wav2lip/resolve/main/wav2lip_gan.pth' -OutFile '%WAV2LIP_MODEL%' -UseBasicParsing -ErrorAction Stop;" ^
    "exit 0" ^
    "} catch { exit 1 }"
if errorlevel 1 goto wav2lip_model_try3_fail
powershell -NoProfile -Command "if ((Get-Item '%WAV2LIP_MODEL%').Length -lt 100MB) { exit 1 } else { exit 0 }"
if not errorlevel 1 goto wav2lip_model_verify
:wav2lip_model_try3_fail
echo  [!] Fallback mirror 2 failed.
if exist "%WAV2LIP_MODEL%" del /Q "%WAV2LIP_MODEL%" >nul 2>&1
goto wav2lip_model_failed

:wav2lip_model_verify
echo  [+] Wav2Lip model downloaded.
goto wav2lip_model_sha

:wav2lip_model_failed
echo  [!] All Wav2Lip model mirrors failed. Lip Sync disabled.
echo  [!] Rest of the installation will continue normally.
goto wav2lip_model_done

:wav2lip_model_sha
:: SHA256 integrity check for the known wav2lip_gan.pth file.
set "WAV2LIP_SHA256=ca9ab7b7b812c0e80a6e70a5977c545a1e8a365a6c49d5e533023c034d7ac3d8"
if not defined WAV2LIP_SHA256 goto wav2lip_sha_skip
set "GOT_SHA256="
for /f %%h in ('powershell -NoProfile -Command "(Get-FileHash '%WAV2LIP_MODEL%' -Algorithm SHA256).Hash.ToLower()"') do set "GOT_SHA256=%%h"
if /i "!GOT_SHA256!"=="!WAV2LIP_SHA256!" goto wav2lip_sha_ok
echo  [!] Wav2Lip model SHA256 mismatch. Expected !WAV2LIP_SHA256!, got !GOT_SHA256!.
del /Q "%WAV2LIP_MODEL%" >nul 2>&1
goto wav2lip_model_done
:wav2lip_sha_ok
echo  [+] Wav2Lip model SHA256 verified.
goto wav2lip_model_done
:wav2lip_sha_skip
echo  [!] WAV2LIP_SHA256 not set - skipping integrity check.
goto wav2lip_model_done

:wav2lip_model_done

echo  [+] Python packages installed.

:: -- 4. Download and install ffmpeg ----------------------------------------
echo.
echo [4/5] Installing ffmpeg...

if exist "%FFMPEG_DIR%\ffmpeg.exe" (
    echo  [+] ffmpeg already present, skipping download.
    goto ffmpeg_done
)

:: Check if PowerShell is available
powershell -Command "exit 0" >nul 2>&1
if errorlevel 1 (
    echo  [!] PowerShell not available. Download ffmpeg manually from:
    echo      https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip
    echo      and extract it to: %FFMPEG_DIR%
    goto ffmpeg_skip
)

echo  [*] Downloading ffmpeg (essentials build ~90MB)...
if not exist "%FFMPEG_DIR%" mkdir "%FFMPEG_DIR%"

powershell -Command ^
    "$url = 'https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip';" ^
    "$zip = '%FFMPEG_DIR%\ffmpeg.zip';" ^
    "Write-Host '     Connecting...';" ^
    "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12;" ^
    "Invoke-WebRequest -Uri $url -OutFile $zip -UseBasicParsing;" ^
    "Write-Host '     Extracting...';" ^
    "Expand-Archive -Path $zip -DestinationPath '%FFMPEG_DIR%\tmp' -Force;" ^
    "$bin = Get-ChildItem '%FFMPEG_DIR%\tmp' -Recurse -Filter 'ffmpeg.exe' | Select-Object -First 1;" ^
    "Copy-Item $bin.FullName '%FFMPEG_DIR%\ffmpeg.exe';" ^
    "$probe = Get-ChildItem '%FFMPEG_DIR%\tmp' -Recurse -Filter 'ffprobe.exe' | Select-Object -First 1;" ^
    "Copy-Item $probe.FullName '%FFMPEG_DIR%\ffprobe.exe';" ^
    "Remove-Item $zip -Force;" ^
    "Remove-Item '%FFMPEG_DIR%\tmp' -Recurse -Force;" ^
    "Write-Host '  [+] ffmpeg installed.'"

if errorlevel 1 (
    echo  [!] ffmpeg download failed. You can download it manually from:
    echo      https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip
    echo      and extract ffmpeg.exe and ffprobe.exe to: %FFMPEG_DIR%
    goto ffmpeg_skip
)

:ffmpeg_done
:: Add ffmpeg to PATH for the current session
set "PATH=%FFMPEG_DIR%;%PATH%"

:: Add ffmpeg to the machine PATH permanently (multi-user, requires admin)
powershell -Command ^
    "$p = [Environment]::GetEnvironmentVariable('PATH','Machine');" ^
    "if ($p -notlike '*%FFMPEG_DIR%*') {" ^
    "  [Environment]::SetEnvironmentVariable('PATH', $p + ';%FFMPEG_DIR%', 'Machine')" ^
    "}"
echo  [+] ffmpeg added to machine PATH.

:: Rimuovi eventuale entry ffmpeg nel vecchio user PATH (cleanup post-legacy)
powershell -Command ^
    "$p = [Environment]::GetEnvironmentVariable('PATH','User');" ^
    "if ($p -and $p -like '*%USERPROFILE%\VideoTranslatorAI\ffmpeg*') {" ^
    "  $new = ($p -split ';' | Where-Object { $_ -notlike '*%USERPROFILE%\VideoTranslatorAI\ffmpeg*' }) -join ';';" ^
    "  [Environment]::SetEnvironmentVariable('PATH', $new, 'User')" ^
    "}"
goto ffmpeg_end

:ffmpeg_skip
echo  [!] ffmpeg not installed - translation will not work without it.

:ffmpeg_end

:: -- 5. Create Desktop shortcut --------------------------------------------
echo.
echo [5/5] Creating Desktop shortcut...

:: Public Desktop → shortcut visibile a tutti gli utenti del PC
set "SHORTCUT=%PUBLIC%\Desktop\Video Translator AI.lnk"

:: Resolve full path to pythonw.exe (avoids PATH lookup issues from desktop)
for /f "tokens=*" %%i in ('python -c "import sys,os; print(os.path.join(os.path.dirname(sys.executable),'pythonw.exe'))"') do set "PYTHONW=%%i"

:: Create the .lnk shortcut via PowerShell - no CMD window, no admin required
powershell -Command ^
    "$ws = New-Object -ComObject WScript.Shell;" ^
    "$s = $ws.CreateShortcut('%SHORTCUT%');" ^
    "$s.TargetPath = '%PYTHONW%';" ^
    "$s.Arguments = [char]34 + '%INSTALL_DIR%\video_translator_gui.py' + [char]34;" ^
    "$s.WorkingDirectory = '%INSTALL_DIR%';" ^
    "$s.Description = 'Video Translator AI';" ^
    "$s.Save();"

if exist "%SHORTCUT%" (
    echo  [+] Desktop shortcut created.
) else (
    echo  [!] Shortcut not created. You can launch the GUI with:
    echo      python "%INSTALL_DIR%\video_translator_gui.py"
)

:: -- Done -----------------------------------------------------------------
echo.
echo  ============================================
echo    Installation complete!
echo  ============================================
echo.
echo   Launch "Video Translator AI" from the Desktop
echo   or run:
echo   python "%INSTALL_DIR%\video_translator_gui.py"
echo.
echo   NOTE: on first use, Whisper will download
echo   the selected model (150MB - 3GB depending on model).
echo.
pause
exit /b 0

:: -- Subroutine: find and activate MSVC compiler environment ------------------
:find_vcvarsall
set "VCVARSALL="
:: Check default VS 2022 BuildTools path (our silent install uses C:\BuildTools)
if exist "C:\BuildTools\VC\Auxiliary\Build\vcvarsall.bat" (
    set "VCVARSALL=C:\BuildTools\VC\Auxiliary\Build\vcvarsall.bat"
    goto activate_vc
)
:: Check standard VS install paths
for %%d in (
    "C:\Program Files\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvarsall.bat"
    "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvarsall.bat"
    "C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvarsall.bat"
    "C:\Program Files (x86)\Microsoft Visual Studio\2019\BuildTools\VC\Auxiliary\Build\vcvarsall.bat"
) do (
    if exist %%d set "VCVARSALL=%%~d"
)
:activate_vc
if defined VCVARSALL (
    call "!VCVARSALL!" x64 >nul 2>&1
)
goto :eof
