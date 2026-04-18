@echo off
setlocal enabledelayedexpansion
title Video Translator AI - Installer
color 0A

:: ── Check Administrator privileges ───────────────────────────────────────────
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

:: ── Installation directory ────────────────────────────────────────────────
set "INSTALL_DIR=%USERPROFILE%\VideoTranslatorAI"
set "FFMPEG_DIR=%INSTALL_DIR%\ffmpeg"
set "SCRIPT_DIR=%~dp0"

:: ── 1. Check / Auto-install Python ───────────────────────────────────────
echo [1/5] Checking Python...
python --version >nul 2>&1
if not errorlevel 1 goto python_found

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
for /f "tokens=*" %%i in ('python --version 2^>^&1') do set PY_VER=%%i
echo  [+] Found: %PY_VER%

:: Require Python 3.9+
python -c "import sys; exit(0 if sys.version_info >= (3,9) else 1)" >nul 2>&1
if errorlevel 1 (
    echo  [!] Python 3.9 or higher is required.
    pause
    exit /b 1
)

:: ── 2. Create installation folder ─────────────────────────────────────────
echo.
echo [2/5] Preparing installation folder...
if not exist "%INSTALL_DIR%" mkdir "%INSTALL_DIR%"
echo  [+] Folder: %INSTALL_DIR%

:: Copy Python scripts to installation folder
echo  [*] Copying scripts...
copy /Y "%SCRIPT_DIR%video_translator.py"     "%INSTALL_DIR%\video_translator.py"     >nul
copy /Y "%SCRIPT_DIR%video_translator_gui.py" "%INSTALL_DIR%\video_translator_gui.py" >nul
if errorlevel 1 (
    echo  [!] Error copying scripts. Make sure the .py files are in the same folder as this .bat
    pause
    exit /b 1
)
echo  [+] Scripts copied.

:: ── 3. Install Python dependencies ────────────────────────────────────────
echo.
echo [3/5] Installing Python dependencies...
echo  [*] Upgrading pip...
python -m pip install --upgrade pip --quiet

set PACKAGES=faster-whisper demucs soundfile edge-tts deep-translator pydub yt-dlp pyloudnorm

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

:: Install Coqui TTS separately (requires C++ Build Tools on Windows)
echo  [*] Installing Coqui TTS (voice cloning)...
python -m pip install Cython setuptools wheel --quiet
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8

:: Helper: activate MSVC compiler environment if vcvarsall.bat is available
call :find_vcvarsall

:: Attempt 1: no-build-isolation (works if VS Build Tools already present)
python -m pip install TTS --no-build-isolation --quiet 2>nul
if not errorlevel 1 goto tts_ok

:: Attempt 2: older stable version
python -m pip install "TTS==0.17.6" --no-build-isolation --quiet 2>nul
if not errorlevel 1 goto tts_ok

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

:: Retry TTS with compiler now active
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

echo  [+] Python packages installed.

:: ── 4. Download and install ffmpeg ────────────────────────────────────────
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

:: ── 5. Create Desktop shortcut ────────────────────────────────────────────
echo.
echo [5/5] Creating Desktop shortcut...

set "SHORTCUT=%USERPROFILE%\Desktop\Video Translator AI.lnk"

:: Resolve full path to pythonw.exe (avoids PATH lookup issues from desktop)
for /f "tokens=*" %%i in ('python -c "import sys,os; print(os.path.join(os.path.dirname(sys.executable),'pythonw.exe'))"') do set "PYTHONW=%%i"

:: Create the .lnk shortcut via PowerShell — no CMD window, no admin required
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

:: ── Done ─────────────────────────────────────────────────────────────────
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

:: ── Subroutine: find and activate MSVC compiler environment ──────────────────
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
