@echo off
:: Use UTF-8 codepage for non-ASCII paths/usernames
chcp 65001 >nul
setlocal enabledelayedexpansion
title Video Translator AI - Installer
color 0A

:: -- Check Administrator privileges -------------------------------------------
net session >nul 2>&1
if errorlevel 1 (
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
)

echo.
echo  ============================================
echo    Video Translator AI - Windows Installer
echo  ============================================
echo.

:: -- Installation directory ------------------------------------------------
set "INSTALL_DIR=%USERPROFILE%\VideoTranslatorAI"
set "FFMPEG_DIR=%INSTALL_DIR%\ffmpeg"
set "SCRIPT_DIR=%~dp0"

:: -- 1. Check / Auto-install Python ---------------------------------------
echo [1/5] Checking Python...
python --version >nul 2>&1
if not errorlevel 1 goto python_found

REM Python 3.11 is the recommended target:
REM   - dlib wheels (z-mahmud22) cover 3.9-3.13
REM   - TTS original package supports up to 3.11
REM   - For Python 3.12+, coqui-tts fork is installed automatically (see below)
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
for /f "tokens=*" %%i in ('powershell -Command "[Environment]::GetEnvironmentVariable(\"PATH\",\"Machine\") + \";\" + [Environment]::GetEnvironmentVariable(\"PATH\",\"User\")"') do set "PATH=%%i"

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

set PACKAGES=faster-whisper demucs soundfile edge-tts deep-translator pydub yt-dlp pyloudnorm sentencepiece sacremoses pyannote.audio torchcodec

:: Python 3.13+ requires audioop-lts
python -c "import sys; exit(0 if sys.version_info >= (3,13) else 1)" >nul 2>&1
if not errorlevel 1 (
    set PACKAGES=%PACKAGES% audioop-lts
)

:: Install PyTorch with CUDA 12.4 (compatible with modern NVIDIA drivers)
echo  [*] Installing PyTorch cu124 + torchaudio...
python -m pip install torch torchaudio --quiet ^
  --index-url https://download.pytorch.org/whl/cu124
if errorlevel 1 (
    echo  [!] PyTorch cu124 failed, trying CPU version...
    python -m pip install torch torchaudio --quiet
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

:: Install transformers with upper bound <5 (isin_mps_friendly removed in 5.x breaks coqui-tts)
echo  [*] Installing transformers ^(^>=4.40.0,^<5^)...
python -m pip install "transformers>=4.40.0,<5" --quiet
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

:: Branch: Python 3.12+ uses the coqui-tts community fork, older Pythons use original TTS
python -c "import sys; exit(0 if sys.version_info >= (3,12) else 1)" >nul 2>&1
if not errorlevel 1 goto tts_py312

echo  [*] Installing Coqui TTS (voice cloning)...
:: Attempt 1: no-build-isolation (works if VS Build Tools already present)
python -m pip install TTS --no-build-isolation --quiet 2>nul
if not errorlevel 1 goto tts_ok

:: Attempt 2: older stable version
python -m pip install "TTS==0.17.6" --no-build-isolation --quiet 2>nul
if not errorlevel 1 goto tts_ok
goto tts_need_buildtools

:tts_py312
echo  [*] Installing coqui-tts fork (Python 3.12+)...
:: Attempt 1: coqui-tts fork with transformers<5 pin
python -m pip install coqui-tts "transformers<5" --no-build-isolation --quiet 2>nul
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

:: Retry TTS with compiler now active (branch again on Python version)
:: Flattened to avoid cmd's parse-time errorlevel evaluation inside if/else blocks
python -c "import sys; exit(0 if sys.version_info >= (3,12) else 1)" >nul 2>&1
if not errorlevel 1 goto retry_py312
goto retry_legacy

:retry_py312
python -m pip install coqui-tts "transformers<5" --no-build-isolation --quiet 2>nul
if not errorlevel 1 goto tts_ok
goto tts_failed

:retry_legacy
python -m pip install TTS --no-build-isolation --quiet 2>nul
if not errorlevel 1 goto tts_ok
python -m pip install "TTS==0.17.6" --no-build-isolation --quiet 2>nul
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
echo  ^|     pip install TTS --no-build-isolation             ^|
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

:: Download Wav2Lip GAN model (~416MB) and clone repo
set "WAV2LIP_DIR=%USERPROFILE%\.local\share\wav2lip"
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
for /f "tokens=*" %%i in ('powershell -Command "[Environment]::GetEnvironmentVariable(\"PATH\",\"Machine\") + \";\" + [Environment]::GetEnvironmentVariable(\"PATH\",\"User\")"') do set "PATH=%%i"

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
powershell -Command ^
    "$url = 'https://huggingface.co/camenduru/Wav2Lip/resolve/main/wav2lip_gan.pth';" ^
    "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12;" ^
    "Invoke-WebRequest -Uri $url -OutFile '%WAV2LIP_MODEL%' -UseBasicParsing;" ^
    "Write-Host '  [+] Wav2Lip model downloaded.'"
if errorlevel 1 (
    echo  [!] Wav2Lip model download failed. Lip Sync disabled.
    if exist "%WAV2LIP_MODEL%" del /Q "%WAV2LIP_MODEL%" >nul 2>&1
)

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

:: Add ffmpeg to the user PATH permanently
powershell -Command ^
    "$p = [Environment]::GetEnvironmentVariable('PATH','User');" ^
    "if ($p -notlike '*%FFMPEG_DIR%*') {" ^
    "  [Environment]::SetEnvironmentVariable('PATH', $p + ';%FFMPEG_DIR%', 'User')" ^
    "}"
echo  [+] ffmpeg added to user PATH.
goto ffmpeg_end

:ffmpeg_skip
echo  [!] ffmpeg not installed - translation will not work without it.

:ffmpeg_end

:: -- 5. Create Desktop shortcut --------------------------------------------
echo.
echo [5/5] Creating Desktop shortcut...

set "SHORTCUT=%USERPROFILE%\Desktop\Video Translator AI.lnk"

:: Resolve full path to pythonw.exe (avoids PATH lookup issues from desktop)
for /f "tokens=*" %%i in ('python -c "import sys,os; print(os.path.join(os.path.dirname(sys.executable),'pythonw.exe'))"') do set "PYTHONW=%%i"

:: Create the .lnk shortcut via PowerShell - no CMD window, no admin required
powershell -Command ^
    "$ws = New-Object -ComObject WScript.Shell;" ^
    "$s = $ws.CreateShortcut('%SHORTCUT%');" ^
    "$s.TargetPath = '%PYTHONW%';" ^
    "$s.Arguments = '\"%INSTALL_DIR%\video_translator_gui.py\"';" ^
    "$s.WorkingDirectory = '%INSTALL_DIR%';" ^
    "$s.Description = 'Video Translator AI';" ^
    "$env:Path = '%FFMPEG_DIR%;' + $env:Path;" ^
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
