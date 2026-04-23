@echo off
:: Use UTF-8 codepage for non-ASCII paths/usernames
chcp 65001 >nul
setlocal enabledelayedexpansion
title Video Translator AI - Uninstaller
color 0E

:: -- Paths (must match install_windows.bat) --------------------------------
set "INSTALL_DIR=%ProgramFiles%\VideoTranslatorAI"
set "FFMPEG_DIR=%INSTALL_DIR%\ffmpeg"
set "PUBLIC_SHORTCUT=%PUBLIC%\Desktop\Video Translator AI.lnk"

:: Per-user (resolved at runtime for the CURRENT user of the console)
set "USER_CONFIG=%USERPROFILE%\.videotranslatorai_config.json"
set "USER_HF_CACHE=%USERPROFILE%\.cache\huggingface"
set "USER_XTTS_CACHE=%LOCALAPPDATA%\tts"
set "USER_LEGACY_DIR=%USERPROFILE%\VideoTranslatorAI"
set "USER_LEGACY_WAV2LIP=%USERPROFILE%\.local\share\wav2lip"
set "USER_LEGACY_SHORTCUT=%USERPROFILE%\Desktop\Video Translator AI.lnk"

:: Detect admin
set "IS_ADMIN=0"
net session >nul 2>&1
if not errorlevel 1 set "IS_ADMIN=1"

:menu
cls
echo.
echo  ============================================
echo    Video Translator AI - Uninstaller
echo  ============================================
echo.
if "%IS_ADMIN%"=="1" (
    echo   Administrator: YES
) else (
    echo   Administrator: NO   [modes 1 and 3 require Admin]
)
echo.
echo   [1] Full uninstall - one click, ALL users
echo       Removes app, shortcut, ffmpeg PATH, every user's config
echo       and model cache, plus the Python AI packages.
echo.
echo   [2] Current user only - no Admin required
echo       Removes only your personal config, model caches
echo       (Whisper/XTTS) and legacy per-user install.
echo       Keeps the system-wide installation for other users.
echo.
echo   [3] Custom - granular, Y/N per category
echo.
echo   [Q] Quit
echo.
set /p "CHOICE=Your choice [1/2/3/Q]: "
if /i "%CHOICE%"=="1" goto full_uninstall
if /i "%CHOICE%"=="2" goto user_uninstall
if /i "%CHOICE%"=="3" goto custom_uninstall
if /i "%CHOICE%"=="q" goto end
goto menu


:: ==========================================================================
:: 1) FULL UNINSTALL (all users, system-wide)
:: ==========================================================================
:full_uninstall
if "%IS_ADMIN%"=="0" (
    echo.
    echo  [!] Administrator privileges required for full uninstall.
    echo      Right-click uninstall_windows.bat and choose "Run as administrator".
    echo.
    pause
    goto menu
)
echo.
echo  ============================================
echo    WARNING: this will remove EVERYTHING
echo  ============================================
echo  - Application folder: %INSTALL_DIR%
echo  - Public Desktop shortcut
echo  - ffmpeg from machine PATH
echo  - All users' HF model caches (Whisper, XTTS)
echo  - All users' VTAI config (HF token)
echo  - All legacy per-user installs
echo  - All Python AI packages (coqui-tts, torch, demucs, ...)
echo.
echo  OPTIONAL (asked below): Python 3.11 and Git for Windows.
echo  NOT removed automatically: VS C++ Build Tools (use "Apps and features").
echo.
set /p "CONFIRM=Type YES (uppercase) to confirm: "
if not "%CONFIRM%"=="YES" (
    echo  Cancelled.
    pause
    goto menu
)
echo.
echo  --- Optional: also uninstall Python 3.11 and Git for Windows? ---
echo  These were installed by install_windows.bat but you may use them for
echo  other projects. Remove them only if you are sure.
echo.
set /p "Q_PY_FULL=Uninstall Python 3.11 ? [Y/N]: "
set /p "Q_GIT_FULL=Uninstall Git for Windows ? [Y/N]: "
echo.
call :remove_app
call :remove_shortcut_public
call :remove_ffmpeg_path
call :remove_legacy_all_users
call :remove_user_configs_all
call :remove_user_caches_all
call :remove_python_packages_all
if /i "%Q_PY_FULL%"=="Y" call :remove_python
if /i "%Q_GIT_FULL%"=="Y" call :remove_git
goto done


:: ==========================================================================
:: 2) CURRENT USER ONLY (no admin)
:: ==========================================================================
:user_uninstall
echo.
echo  ============================================
echo    Current user only ( %USERNAME% )
echo  ============================================
echo  - VTAI config file ( %USER_CONFIG% )
echo  - HF model cache (Whisper, XTTS)
echo  - Legacy per-user install, if present
echo.
echo  The system-wide installation will stay intact for other users.
echo.
set /p "CONFIRM=Proceed? [Y/N]: "
if /i not "%CONFIRM%"=="Y" (
    echo  Cancelled.
    pause
    goto menu
)
echo.
call :remove_user_config_current
call :remove_user_cache_current
call :remove_legacy_current_user
goto done


:: ==========================================================================
:: 3) CUSTOM (granular, Y/N per category)
:: ==========================================================================
:custom_uninstall
echo.
echo  Custom uninstall - answer Y or N for each item.
echo  ( items marked [ADMIN] need administrator privileges )
echo.

:: -- System-wide items (admin) --------------------------------------------
if "%IS_ADMIN%"=="1" (
    set /p "Q_APP=[ADMIN] Remove application folder %INSTALL_DIR% ? [Y/N]: "
    if /i "!Q_APP!"=="Y" call :remove_app

    set /p "Q_SC=[ADMIN] Remove Public Desktop shortcut ? [Y/N]: "
    if /i "!Q_SC!"=="Y" call :remove_shortcut_public

    set /p "Q_PATH=[ADMIN] Remove ffmpeg from machine PATH ? [Y/N]: "
    if /i "!Q_PATH!"=="Y" call :remove_ffmpeg_path

    set /p "Q_LEG=[ADMIN] Remove legacy per-user installs for ALL users ? [Y/N]: "
    if /i "!Q_LEG!"=="Y" call :remove_legacy_all_users

    set /p "Q_CFG_ALL=[ADMIN] Remove VTAI config file (HF token) for ALL users ? [Y/N]: "
    if /i "!Q_CFG_ALL!"=="Y" call :remove_user_configs_all

    set /p "Q_CACHE_ALL=[ADMIN] Remove HF model cache (Whisper+XTTS, ~3-5 GB) for ALL users ? [Y/N]: "
    if /i "!Q_CACHE_ALL!"=="Y" call :remove_user_caches_all
) else (
    echo  [!] Skipping system-wide items - run as Administrator to access them.
    echo.
)

:: -- Current user items (no admin needed) ---------------------------------
echo.
echo  --- Items for the current user ( %USERNAME% ) ---
set /p "Q_CFG=Remove your VTAI config file (HF token) ? [Y/N]: "
if /i "!Q_CFG!"=="Y" call :remove_user_config_current

set /p "Q_CACHE=Remove your HF model cache (Whisper, XTTS) ? [Y/N]: "
if /i "!Q_CACHE!"=="Y" call :remove_user_cache_current

set /p "Q_LEG_ME=Remove legacy per-user install for your account ? [Y/N]: "
if /i "!Q_LEG_ME!"=="Y" call :remove_legacy_current_user

:: -- Python packages (grouped, admin recommended) -------------------------
echo.
echo  --- Python AI packages (installed system-wide) ---
where python >nul 2>&1
if errorlevel 1 (
    echo  [!] python not found in PATH, skipping package removal.
    goto done
)
if "%IS_ADMIN%"=="0" (
    echo  [!] Not running as Admin: pip may fail for system-wide packages.
)

set /p "Q_TTS=Remove TTS group (coqui-tts, transformers) ? [Y/N]: "
if /i "!Q_TTS!"=="Y" python -m pip uninstall -y coqui-tts transformers

set /p "Q_TORCH=Remove PyTorch stack (torch, torchaudio, torchvision, torchcodec) ? [Y/N]: "
if /i "!Q_TORCH!"=="Y" python -m pip uninstall -y torch torchaudio torchvision torchcodec

set /p "Q_WHI=Remove Whisper + ctranslate2 ? [Y/N]: "
if /i "!Q_WHI!"=="Y" python -m pip uninstall -y faster-whisper ctranslate2

set /p "Q_DEM=Remove Demucs ? [Y/N]: "
if /i "!Q_DEM!"=="Y" python -m pip uninstall -y demucs

set /p "Q_W2L=Remove Wav2Lip deps (basicsr, facexlib, dlib) ? [Y/N]: "
if /i "!Q_W2L!"=="Y" python -m pip uninstall -y basicsr facexlib dlib

set /p "Q_PYA=Remove pyannote.audio (speaker diarization) ? [Y/N]: "
if /i "!Q_PYA!"=="Y" python -m pip uninstall -y pyannote.audio

set /p "Q_MIS=Remove pipeline utilities (yt-dlp, edge-tts, deep-translator, pydub, pyloudnorm, soundfile, sacremoses, sentencepiece) ? [Y/N]: "
if /i "!Q_MIS!"=="Y" python -m pip uninstall -y yt-dlp edge-tts deep-translator pydub pyloudnorm soundfile sacremoses sentencepiece

:: -- System tools (Admin, must be last) ------------------------------------
if "%IS_ADMIN%"=="1" (
    echo.
    echo  --- System-wide tools installed by install_windows.bat ---
    echo  ( remove only if you do not use them for other projects )
    set /p "Q_PY=[ADMIN] Uninstall Python 3.11 ? [Y/N]: "
    if /i "!Q_PY!"=="Y" call :remove_python

    set /p "Q_GIT=[ADMIN] Uninstall Git for Windows ? [Y/N]: "
    if /i "!Q_GIT!"=="Y" call :remove_git
)

goto done


:: ==========================================================================
:: DONE
:: ==========================================================================
:done
echo.
echo  ============================================
echo    Uninstall complete
echo  ============================================
echo.
echo  If anything was skipped or you want to double-check, open
echo  "Apps and features" (Windows Settings) - entries like
echo  "Python 3.11.9", "Git" or "Visual Studio Build Tools"
echo  can be removed from there manually.
echo.
pause
goto end

:end
endlocal
exit /b 0


:: ==========================================================================
:: FUNCTIONS
:: ==========================================================================

:remove_app
echo  [*] Removing %INSTALL_DIR% ...
if exist "%INSTALL_DIR%" (
    rmdir /S /Q "%INSTALL_DIR%" 2>nul
    if exist "%INSTALL_DIR%" (
        echo  [!] Some files could not be removed. Close any running Video Translator AI and retry.
    ) else (
        echo  [+] Removed.
    )
) else (
    echo  [-] Not found, skipping.
)
exit /b 0

:remove_shortcut_public
echo  [*] Removing Public Desktop shortcut ...
if exist "%PUBLIC_SHORTCUT%" (
    del /Q "%PUBLIC_SHORTCUT%" 2>nul
    echo  [+] Removed.
) else (
    echo  [-] Not found, skipping.
)
exit /b 0

:remove_ffmpeg_path
echo  [*] Removing ffmpeg from machine PATH ...
powershell -NoProfile -Command ^
    "$p = [Environment]::GetEnvironmentVariable('PATH','Machine');" ^
    "if ($p) {" ^
    "  $new = ($p -split ';' | Where-Object { $_ -and $_ -notlike '*VideoTranslatorAI\ffmpeg*' }) -join ';';" ^
    "  if ($new -ne $p) {" ^
    "    [Environment]::SetEnvironmentVariable('PATH', $new, 'Machine');" ^
    "    Write-Host '  [+] Removed from machine PATH.'" ^
    "  } else { Write-Host '  [-] Not in machine PATH, skipping.' }" ^
    "}"
exit /b 0

:remove_legacy_all_users
echo  [*] Removing legacy per-user installs for all Windows users ...
for /d %%U in ("%SystemDrive%\Users\*") do (
    if exist "%%~U\VideoTranslatorAI" (
        echo      - %%~nxU : legacy app folder
        rmdir /S /Q "%%~U\VideoTranslatorAI" 2>nul
    )
    if exist "%%~U\.local\share\wav2lip" (
        echo      - %%~nxU : legacy wav2lip
        rmdir /S /Q "%%~U\.local\share\wav2lip" 2>nul
    )
    if exist "%%~U\Desktop\Video Translator AI.lnk" (
        echo      - %%~nxU : legacy shortcut
        del /Q "%%~U\Desktop\Video Translator AI.lnk" 2>nul
    )
)
echo  [+] Done.
exit /b 0

:remove_legacy_current_user
echo  [*] Removing legacy per-user install for %USERNAME% ...
if exist "%USER_LEGACY_DIR%" rmdir /S /Q "%USER_LEGACY_DIR%" 2>nul
if exist "%USER_LEGACY_WAV2LIP%" rmdir /S /Q "%USER_LEGACY_WAV2LIP%" 2>nul
if exist "%USER_LEGACY_SHORTCUT%" del /Q "%USER_LEGACY_SHORTCUT%" 2>nul
echo  [+] Done.
exit /b 0

:remove_user_configs_all
echo  [*] Removing VTAI config files for all users ...
for /d %%U in ("%SystemDrive%\Users\*") do (
    if exist "%%~U\.videotranslatorai_config.json" (
        echo      - %%~nxU
        del /Q "%%~U\.videotranslatorai_config.json" 2>nul
    )
)
echo  [+] Done.
exit /b 0

:remove_user_config_current
echo  [*] Removing VTAI config for %USERNAME% ...
if exist "%USER_CONFIG%" (
    del /Q "%USER_CONFIG%" 2>nul
    echo  [+] Removed.
) else (
    echo  [-] Not found.
)
exit /b 0

:remove_user_caches_all
echo  [*] Removing HF + XTTS model caches for all users ...
for /d %%U in ("%SystemDrive%\Users\*") do (
    if exist "%%~U\.cache\huggingface\hub" (
        for /d %%M in ("%%~U\.cache\huggingface\hub\models--*") do (
            echo %%~nxM | findstr /i "whisper XTTS coqui wav2vec pyannote" >nul && rmdir /S /Q "%%~M" 2>nul
        )
    )
    if exist "%%~U\AppData\Local\tts" (
        echo      - %%~nxU : XTTS cache
        rmdir /S /Q "%%~U\AppData\Local\tts" 2>nul
    )
)
echo  [+] Done.
exit /b 0

:remove_user_cache_current
echo  [*] Removing HF + XTTS model cache for %USERNAME% ...
if exist "%USER_HF_CACHE%\hub" (
    for /d %%M in ("%USER_HF_CACHE%\hub\models--*") do (
        echo %%~nxM | findstr /i "whisper XTTS coqui wav2vec pyannote" >nul && rmdir /S /Q "%%~M" 2>nul
    )
)
if exist "%USER_XTTS_CACHE%" rmdir /S /Q "%USER_XTTS_CACHE%" 2>nul
echo  [+] Done.
exit /b 0

:remove_python_packages_all
echo  [*] Removing all Python AI packages ...
where python >nul 2>&1
if errorlevel 1 (
    echo  [!] python not found in PATH, skipping.
    exit /b 0
)
python -m pip uninstall -y ^
    coqui-tts transformers ^
    torch torchaudio torchvision torchcodec ^
    faster-whisper ctranslate2 ^
    demucs ^
    basicsr facexlib dlib ^
    pyannote.audio ^
    yt-dlp edge-tts deep-translator pydub pyloudnorm soundfile sacremoses sentencepiece 2>nul
echo  [+] Done.
exit /b 0

:remove_python
:: Silent uninstall of Python 3.11 via registry QuietUninstallString.
:: Handles both per-user and system-wide installs.
echo  [*] Uninstalling Python 3.11 ...
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
    "$roots = 'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall','HKLM:\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall','HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall';" ^
    "$found = foreach ($r in $roots) { if (Test-Path $r) { Get-ChildItem $r -ErrorAction SilentlyContinue | ForEach-Object { Get-ItemProperty $_.PSPath -ErrorAction SilentlyContinue } | Where-Object { $_.DisplayName -match '^Python 3\.11' -and ($_.QuietUninstallString -or $_.UninstallString) } } };" ^
    "if (-not $found) { Write-Host '  [-] Python 3.11 not found in uninstall registry.'; exit 0 };" ^
    "foreach ($u in $found) {" ^
    "    Write-Host ('  [*] ' + $u.DisplayName);" ^
    "    $cmd = if ($u.QuietUninstallString) { $u.QuietUninstallString } else { $u.UninstallString + ' /quiet' };" ^
    "    try { Start-Process -FilePath 'cmd.exe' -ArgumentList '/c', $cmd -Wait -NoNewWindow; Write-Host '  [+] Done.' }" ^
    "    catch { Write-Host ('  [!] Failed: ' + $_.Exception.Message) }" ^
    "}"
exit /b 0

:remove_git
:: Silent uninstall of Git for Windows (Inno Setup) via registry UninstallString.
echo  [*] Uninstalling Git for Windows ...
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
    "$roots = 'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall','HKLM:\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall','HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall';" ^
    "$found = foreach ($r in $roots) { if (Test-Path $r) { Get-ChildItem $r -ErrorAction SilentlyContinue | ForEach-Object { Get-ItemProperty $_.PSPath -ErrorAction SilentlyContinue } | Where-Object { $_.DisplayName -match '^Git( |$)' -and $_.DisplayName -notmatch 'LFS|Extensions' -and $_.UninstallString } } };" ^
    "if (-not $found) { Write-Host '  [-] Git for Windows not found.'; exit 0 };" ^
    "foreach ($u in $found) {" ^
    "    Write-Host ('  [*] ' + $u.DisplayName);" ^
    "    $exe = ($u.UninstallString -replace '\"','').Trim();" ^
    "    if (Test-Path $exe) {" ^
    "        try { Start-Process -FilePath $exe -ArgumentList '/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART' -Wait; Write-Host '  [+] Done.' }" ^
    "        catch { Write-Host ('  [!] Failed: ' + $_.Exception.Message) }" ^
    "    } else { Write-Host ('  [!] Uninstaller not found at ' + $exe) }" ^
    "}"
exit /b 0
