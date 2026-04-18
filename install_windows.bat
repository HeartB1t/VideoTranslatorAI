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

:: ── 1. Check Python ───────────────────────────────────────────────────────
echo [1/5] Checking Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo  [!] Python not found!
    echo      Download it from: https://www.python.org/downloads/
    echo      Make sure to check "Add Python to PATH" during installation.
    echo.
    pause
    exit /b 1
)
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

set PACKAGES=faster-whisper demucs soundfile edge-tts deep-translator pydub yt-dlp TTS

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

echo  [*] Installing packages: %PACKAGES%
python -m pip install %PACKAGES% --quiet
if errorlevel 1 (
    echo  [!] Error installing Python packages.
    pause
    exit /b 1
)
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
set "LAUNCHER=%INSTALL_DIR%\launch.bat"

:: Create a launcher.bat (runs without a visible cmd window)
(
    echo @echo off
    echo cd /d "%INSTALL_DIR%"
    echo set "PATH=%FFMPEG_DIR%;%%PATH%%"
    echo pythonw "%INSTALL_DIR%\video_translator_gui.py"
) > "%LAUNCHER%"

:: Create the .lnk shortcut via PowerShell
powershell -Command ^
    "$ws = New-Object -ComObject WScript.Shell;" ^
    "$s = $ws.CreateShortcut('%SHORTCUT%');" ^
    "$s.TargetPath = 'pythonw';" ^
    "$s.Arguments = '\"%INSTALL_DIR%\video_translator_gui.py\"';" ^
    "$s.WorkingDirectory = '%INSTALL_DIR%';" ^
    "$s.Description = 'Video Translator AI';" ^
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
