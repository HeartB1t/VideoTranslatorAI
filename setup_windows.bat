@echo off
:: ============================================================================
::  Video Translator AI - Unified Windows Setup
::  Modes: install | repair | uninstall (interactive menu or CLI argument)
:: ============================================================================
setlocal enabledelayedexpansion
:: The console keeps its own code page. powershell.exe, started while the
:: console is at 65001 (UTF-8), turns the default TrueType font into the
:: raster "Terminal" (measured on Windows 11: Consolas became Terminal 8x12 at
:: the first powershell.exe, with any flags or redirections; chcp alone and
:: other programs kept the font). UTF-8 is set only while the script writes
:: the setup log or reads the PATH file of :reload_path, both UTF-8, so user
:: names and folders outside ASCII stay intact there. VTAI_CP is the number
:: at the end of chcp's localized line ("Active code page: 850", "Aktive
:: Codepage: 850."); when it cannot be read, nothing is switched.
set "VTAI_CHCP=%SystemRoot%\System32\chcp.com"
set "VTAI_CP="
for /f "tokens=*" %%a in ('"%VTAI_CHCP%"') do set "VTAI_CP=%%a"
for %%t in (%VTAI_CP%) do set "VTAI_CP=%%t"
if defined VTAI_CP set "VTAI_CP=%VTAI_CP:.=%"
echo(%VTAI_CP%| findstr /r /x "[0-9][0-9]*" >nul || set "VTAI_CP="

set "SCRIPT_VERSION=2.1.4"
title Video Translator AI - Setup v%SCRIPT_VERSION%

:: -- Centralised paths (single source of truth) ------------------------------
set "INSTALL_DIR=%ProgramFiles%\VideoTranslatorAI"
set "FFMPEG_DIR=%INSTALL_DIR%\ffmpeg"
set "MPV_DIR=%INSTALL_DIR%\mpv-runtime"
set "WAV2LIP_DIR=%INSTALL_DIR%\wav2lip"
set "WAV2LIP_REPO=%WAV2LIP_DIR%\Wav2Lip"
set "WAV2LIP_MODEL=%WAV2LIP_DIR%\wav2lip_gan.pth"
set "WAV2LIP_SHA256=ca9ab7b7b812c0e80a6e70a5977c545a1e8a365a6c49d5e533023c034d7ac3d8"
set "PUBLIC_SHORTCUT=%PUBLIC%\Desktop\Video Translator AI.lnk"
set "START_MENU_DIR=%ProgramData%\Microsoft\Windows\Start Menu\Programs\Video Translator AI"
set "ICON_PATH=%INSTALL_DIR%\assets\icon.ico"
set "SCRIPT_DIR=%~dp0"
:: Profiles are copied beside the installed application for offline repair.
set "CORE_REQUIREMENTS=%INSTALL_DIR%\requirements-core.txt"
set "OPTIONAL_REQUIREMENTS=%INSTALL_DIR%\requirements-optional.txt"
set "GPU_REQUIREMENTS=%INSTALL_DIR%\requirements-gpu-cu124.txt"
set "PLAYER_REQUIREMENTS=%INSTALL_DIR%\requirements-player.txt"
:: A new release is unpacked here before the hand-over. Program Files, never
:: %TEMP%: only administrators can write it, so a non-elevated process cannot
:: swap the verified files before this elevated script runs them.
set "UPDATE_DIR=%INSTALL_DIR%\_update"
:: Setup log: one timestamped line per step and per outcome, for install,
:: repair and uninstall. Lives in the profile root so an uninstall (which
:: wipes AppData, Temp and the install folder) never deletes it.
set "VTAI_SETUP_LOG=%USERPROFILE%\VideoTranslatorAI-setup.log"

:: Update hand-over (see :update_prepare). The previous run sets
:: VTAI_UPDATE_HANDOFF=1 just before starting this script: read it once and
:: clear it at once. It only stops a second update check and the Proceed
:: prompt; it never proves that anything was verified.
set "VTAI_HANDED_OVER=%VTAI_UPDATE_HANDOFF%"
set "VTAI_UPDATE_HANDOFF="
set "VTAI_NEW_SETUP="

:: Per-user paths resolved at runtime for the CURRENT console user
set "USER_CONFIG=%USERPROFILE%\.videotranslatorai_config.json"
set "USER_HF_CACHE=%USERPROFILE%\.cache\huggingface"
set "USER_XTTS_CACHE=%LOCALAPPDATA%\tts"
set "USER_MPV_RUNTIME=%LOCALAPPDATA%\VideoTranslatorAI\mpv-runtime"
:: Current data locations: config + daily logs (Roaming), player and JS
:: runtimes (Local), live-mode cache and shaders (Temp).
set "USER_APP_DATA=%APPDATA%\VideoTranslatorAI"
set "USER_LOCAL_DATA=%LOCALAPPDATA%\VideoTranslatorAI"
set "USER_TEMP_DATA=%TEMP%\VideoTranslatorAI"
set "USER_LEGACY_DIR=%USERPROFILE%\VideoTranslatorAI"
set "USER_LEGACY_WAV2LIP=%USERPROFILE%\.local\share\wav2lip"
set "USER_LEGACY_SHORTCUT=%USERPROFILE%\Desktop\Video Translator AI.lnk"

:: Detect admin once, expose as IS_ADMIN=0/1
call :check_admin

:: -- Argument dispatch (CLI mode) --------------------------------------------
set "MODE="
if /i "%~1"=="install"   set "MODE=install"
if /i "%~1"=="repair"    set "MODE=repair"
if /i "%~1"=="update"    set "MODE=repair"
if /i "%~1"=="uninstall" set "MODE=uninstall"
if /i "%~1"=="/?"        goto show_help
if /i "%~1"=="-h"        goto show_help
if /i "%~1"=="--help"    goto show_help
if /i "%~1"=="help"      goto show_help

if defined MODE goto dispatch

:: -- Interactive menu --------------------------------------------------------
:menu
cls
color 0B
echo.
echo  ============================================
echo    Video Translator AI - Windows Setup v%SCRIPT_VERSION%
echo  ============================================
echo.
if "%IS_ADMIN%"=="1" (
    echo   Administrator: YES
) else (
    echo   Administrator: NO   [modes 1, 2 and 3 require Admin]
)
echo.
echo   [1] Install         (first-time setup)
echo   [2] Repair / Update (latest release from GitHub, keep config)
echo   [3] Uninstall       (granular menu inside)
echo   [Q] Quit
echo.
set "CHOICE="
set /p "CHOICE=Your choice [1/2/3/Q]: "
if /i "%CHOICE%"=="1" set "MODE=install"   & goto dispatch
if /i "%CHOICE%"=="2" set "MODE=repair"    & goto dispatch
if /i "%CHOICE%"=="3" set "MODE=uninstall" & goto dispatch
if /i "%CHOICE%"=="q" goto end
goto menu

:dispatch
if "%IS_ADMIN%"=="0" (
    color 0C
    echo.
    echo  ============================================
    echo    ERROR: Administrator privileges required
    echo  ============================================
    echo.
    echo  Right-click setup_windows.bat and choose
    echo  "Run as administrator", then try again.
    echo.
    pause
    exit /b 1
)
if /i "%MODE%"=="install"   goto mode_install
if /i "%MODE%"=="repair"    goto mode_repair
if /i "%MODE%"=="uninstall" goto mode_uninstall
goto menu


:: ============================================================================
:: HELP
:: ============================================================================
:show_help
echo.
echo  Video Translator AI - Setup v%SCRIPT_VERSION%
echo.
echo  Usage:
echo    setup_windows.bat              Interactive menu
echo    setup_windows.bat install      First-time install
echo    setup_windows.bat repair       Repair / update an existing install
echo    setup_windows.bat update       Same as repair: gets the latest release first
echo    setup_windows.bat uninstall    Uninstall (granular menu)
echo    setup_windows.bat /?           This help
echo.
echo  All modes require Administrator privileges.
echo.
exit /b 0


:: ============================================================================
:: MODE: INSTALL  (first-time setup)
:: ============================================================================
:mode_install
color 0A
call :print_banner "Video Translator AI - Installer"
call :log_session "INSTALL"

call :preflight_arch    || ( call :logfile "Preflight architecture: FAILED" & exit /b 1 )
call :preflight_disk    || ( call :logfile "Preflight disk space: FAILED" & exit /b 1 )
call :preflight_network || ( call :logfile "Preflight Internet: FAILED" & exit /b 1 )
call :logfile "Preflight architecture, disk space and Internet: ok"

call :legacy_cleanup_current

call :step_python   "1/6"
if errorlevel 1 ( call :logfile "Step 1/6 Python: FAILED - install stopped" & pause & exit /b 1 )

call :step_copy_files "2/6"
if errorlevel 1 ( call :logfile "Step 2/6 copy files: FAILED - install stopped" & pause & exit /b 1 )

call :step_install_deps "3/6" "0"
if errorlevel 1 ( call :logfile "Step 3/6 Python packages: FAILED - install stopped" & pause & exit /b 1 )

call :step_ffmpeg "4/6" "0"
call :step_player "5/6"
call :step_shortcut "6/6"

call :validate_install
if errorlevel 1 ( call :logfile "RESULT: installation incomplete" & pause & exit /b 1 )
call :player_check
call :logfile "RESULT: installation complete"
call :print_done "Installation complete"
exit /b 0


:: ============================================================================
:: MODE: REPAIR  (refresh existing install, keep user config)
:: ============================================================================
:mode_repair
color 0E
call :print_banner "Video Translator AI - Repair / Update"
call :log_session "REPAIR"
if "%VTAI_HANDED_OVER%"=="1" (
    echo  [*] Continuing the update with the installer of the new release.
    call :logfile "Update: this run is the installer of the new release, from %SCRIPT_DIR%"
    goto repair_confirmed
)
echo.
echo  This will:
echo    - Check GitHub for a newer release and install it
echo    - Re-copy the application files and assets
echo    - Re-run pip install to pick up new/missing packages
echo    - Install or re-check the integrated video player (optional)
echo    - Re-create the Desktop shortcut and the Start Menu entries
echo    - Skip Python / Git / ffmpeg if already installed
echo    - Keep your config (HF token in keyring stays intact)
echo.
set "CONFIRM="
set /p "CONFIRM=Proceed? [Y/N]: "
if /i not "%CONFIRM%"=="Y" (
    echo  Cancelled.
    call :logfile "Repair cancelled by the user"
    pause
    goto end
)
:repair_confirmed

if not exist "%INSTALL_DIR%" (
    echo.
    echo  [^^!] %INSTALL_DIR% not found.
    echo      Repair requires an existing install. Use the Install mode instead.
    call :logfile "Repair stopped: %INSTALL_DIR% not found, use Install instead"
    pause
    goto end
)

call :preflight_network || ( call :logfile "Preflight Internet: FAILED" & exit /b 1 )
call :logfile "Preflight Internet: ok"

call :step_python   "1/6"
if errorlevel 1 ( call :logfile "Step 1/6 Python: FAILED - repair stopped" & pause & exit /b 1 )

if not "%VTAI_HANDED_OVER%"=="1" call :update_prepare
if defined VTAI_NEW_SETUP goto repair_handover

call :step_copy_files "2/6"
if errorlevel 1 ( call :logfile "Step 2/6 copy files: FAILED - repair stopped" & pause & exit /b 1 )

call :step_install_deps "3/6" "1"

call :step_ffmpeg "4/6" "1"

call :step_player "5/6"

:: Always: an older install gets the new Start Menu entries too.
call :step_shortcut "6/6"

call :validate_install
if errorlevel 1 ( call :logfile "RESULT: repair incomplete" & pause & exit /b 1 )
call :player_check
call :logfile "RESULT: repair complete"
call :print_done "Repair complete"
exit /b 0

:: Hand-over to the installer of the new release, verified and unpacked by
:: :update_prepare. This MUST stay a top-level line of this flow, reached by
:: goto: outside any parentheses and outside any called subroutine. A batch
:: file started without `call` replaces this one and cmd never reads this
:: file again, so the new installer may overwrite it; a pending `call` frame
:: would send cmd back into the overwritten file. Delayed expansion goes off
:: first so a path with ! stays intact.
:repair_handover
echo.
echo  [*] Starting the installer of the new release...
call :logfile "Update: handing over to the installer of the new release"
set "VTAI_UPDATE_HANDOFF=1"
setlocal DisableDelayedExpansion
"%VTAI_NEW_SETUP%" repair


:: ============================================================================
:: MODE: UNINSTALL  (granular menu, ported from uninstall_windows.bat)
:: ============================================================================
:mode_uninstall
color 0E
call :log_session "UNINSTALL"
:uninst_menu
cls
echo.
echo  ============================================
echo    Video Translator AI - Uninstaller v%SCRIPT_VERSION%
echo  ============================================
echo.
echo   Administrator: YES
echo.
echo   [1] Full uninstall - one click, ALL users
echo       Removes app, shortcut, ffmpeg PATH, every user's config
echo       and model cache, plus the Python AI packages.
echo.
echo   [2] Current user only
echo       Removes only your personal config, model caches
echo       (Whisper/XTTS) and legacy per-user install.
echo       Keeps the system-wide installation for other users.
echo.
echo   [3] Custom - granular, Y/N per category
echo.
echo   [Q] Quit
echo.
set "UCHOICE="
set /p "UCHOICE=Your choice [1/2/3/Q]: "
call :logfile "Uninstall menu: choice %UCHOICE%"
if /i "%UCHOICE%"=="1" goto uninst_full
if /i "%UCHOICE%"=="2" goto uninst_user
if /i "%UCHOICE%"=="3" goto uninst_custom
if /i "%UCHOICE%"=="q" goto end
goto uninst_menu


:uninst_full
echo.
echo  ============================================
echo    WARNING: this will remove EVERYTHING
echo  ============================================
echo  - Application folder: %INSTALL_DIR%
echo  - Desktop shortcut and Start Menu entries
echo  - ffmpeg from machine PATH
echo  - All users' HF model caches (Whisper, XTTS, MarianMT)
echo  - All users' VTAI config, logs, player/JS runtimes and temp files
echo  - Your saved keys (HF token, ElevenLabs) in Windows Credential Manager
echo  - All legacy per-user installs
echo  - All Python AI packages (coqui-tts, torch, demucs, ...)
echo.
echo  OPTIONAL (asked below): Python 3.11, Git for Windows, Ollama.
echo  NOT removed automatically: VS C++ Build Tools (use "Apps and features").
echo.
set "CONFIRM="
set /p "CONFIRM=Type YES (uppercase) to confirm: "
if not "%CONFIRM%"=="YES" (
    echo  Cancelled.
    call :logfile "Full uninstall: cancelled by the user"
    pause
    goto uninst_menu
)
echo.
echo  --- Optional: also uninstall Python 3.11, Git, and Ollama? ---
set "Q_PY_FULL="
set "Q_GIT_FULL="
set "Q_OLL_FULL="
set /p "Q_PY_FULL=Uninstall Python 3.11 and its per-user packages ? [Y/N]: "
set /p "Q_GIT_FULL=Uninstall Git for Windows ? [Y/N]: "
set /p "Q_OLL_FULL=Uninstall Ollama (also wipes downloaded models, can be GB) ? [Y/N]: "
echo.
call :logfile "Full uninstall: confirmed. Also remove Python=%Q_PY_FULL% Git=%Q_GIT_FULL% Ollama=%Q_OLL_FULL%"
call :remove_app
call :remove_shortcut_public
call :remove_ffmpeg_path
call :remove_legacy_all_users
call :remove_user_configs_all
call :remove_user_caches_all
call :remove_saved_keys
call :remove_python_packages_all
if /i "%Q_PY_FULL%"=="Y" call :remove_python
if /i "%Q_GIT_FULL%"=="Y" call :remove_git
if /i "%Q_OLL_FULL%"=="Y" call :remove_ollama
goto uninst_done


:uninst_user
echo.
echo  ============================================
echo    Current user only ( %USERNAME% )
echo  ============================================
echo  - VTAI config and logs ( %USER_APP_DATA% )
echo  - HF model cache (Whisper, XTTS, MarianMT), player/JS runtimes, temp files
echo  - Saved keys (HF token, ElevenLabs) in Windows Credential Manager
echo  - Legacy per-user install, if present
echo.
echo  The system-wide installation will stay intact for other users.
echo.
set "CONFIRM="
set /p "CONFIRM=Proceed? [Y/N]: "
if /i not "%CONFIRM%"=="Y" (
    echo  Cancelled.
    call :logfile "Current user uninstall: cancelled by the user"
    pause
    goto uninst_menu
)
echo.
call :logfile "Current user uninstall: confirmed for %USERNAME%"
call :remove_user_config_current
call :remove_user_cache_current
call :remove_saved_keys
call :remove_legacy_current_user
goto uninst_done


:uninst_custom
echo.
echo  Custom uninstall - answer Y or N for each item.
echo.
call :logfile "Custom uninstall: started, each removed item is logged below"

set "Q_APP="
set /p "Q_APP=Remove application folder %INSTALL_DIR% ? [Y/N]: "
if /i "!Q_APP!"=="Y" call :remove_app

set "Q_SC="
set /p "Q_SC=Remove the Desktop shortcut and Start Menu entries ? [Y/N]: "
if /i "!Q_SC!"=="Y" call :remove_shortcut_public

set "Q_PATH="
set /p "Q_PATH=Remove ffmpeg from machine PATH ? [Y/N]: "
if /i "!Q_PATH!"=="Y" call :remove_ffmpeg_path

set "Q_LEG="
set /p "Q_LEG=Remove legacy per-user installs for ALL users ? [Y/N]: "
if /i "!Q_LEG!"=="Y" call :remove_legacy_all_users

set "Q_CFG_ALL="
set /p "Q_CFG_ALL=Remove VTAI config and logs for ALL users ? [Y/N]: "
if /i "!Q_CFG_ALL!"=="Y" call :remove_user_configs_all

set "Q_CACHE_ALL="
set /p "Q_CACHE_ALL=Remove model caches (Whisper, XTTS, MarianMT, ~3-5 GB), runtimes and temp files for ALL users ? [Y/N]: "
if /i "!Q_CACHE_ALL!"=="Y" call :remove_user_caches_all

echo.
echo  --- Items for the current user ( %USERNAME% ) ---
set "Q_CFG="
set /p "Q_CFG=Remove your VTAI config and logs ? [Y/N]: "
if /i "!Q_CFG!"=="Y" call :remove_user_config_current

set "Q_KEYS="
set /p "Q_KEYS=Remove your saved keys (HF token, ElevenLabs) from Credential Manager ? [Y/N]: "
if /i "!Q_KEYS!"=="Y" call :remove_saved_keys

set "Q_CACHE="
set /p "Q_CACHE=Remove your model caches (Whisper, XTTS, MarianMT), runtimes and temp files ? [Y/N]: "
if /i "!Q_CACHE!"=="Y" call :remove_user_cache_current

set "Q_LEG_ME="
set /p "Q_LEG_ME=Remove legacy per-user install for your account ? [Y/N]: "
if /i "!Q_LEG_ME!"=="Y" call :remove_legacy_current_user

echo.
echo  --- Python AI packages (installed system-wide) ---
where python >nul 2>&1
if errorlevel 1 (
    echo  [^^!] python not found in PATH, skipping package removal.
    goto uninst_custom_tools
)
if not defined PYTHON_EXE (
    for /f "tokens=*" %%i in ('where python 2^>nul') do (
        if not defined PYTHON_EXE set "PYTHON_EXE=%%i"
    )
)
if not defined PYTHON_EXE set "PYTHON_EXE=python"

set "Q_TTS="
set /p "Q_TTS=Remove TTS group (coqui-tts, transformers) ? [Y/N]: "
if /i "!Q_TTS!"=="Y" call :pip_remove coqui-tts transformers
if /i "!Q_TTS!"=="Y" call :logfile "Custom uninstall: pip uninstall coqui-tts transformers - code !ERRORLEVEL!"

set "Q_TORCH="
set /p "Q_TORCH=Remove PyTorch stack (torch, torchaudio, torchvision, torchcodec) ? [Y/N]: "
if /i "!Q_TORCH!"=="Y" call :pip_remove torch torchaudio torchvision torchcodec
if /i "!Q_TORCH!"=="Y" call :logfile "Custom uninstall: pip uninstall torch torchaudio torchvision torchcodec - code !ERRORLEVEL!"

set "Q_WHI="
set /p "Q_WHI=Remove Whisper + ctranslate2 ? [Y/N]: "
if /i "!Q_WHI!"=="Y" call :pip_remove faster-whisper ctranslate2
if /i "!Q_WHI!"=="Y" call :logfile "Custom uninstall: pip uninstall faster-whisper ctranslate2 - code !ERRORLEVEL!"

set "Q_DEM="
set /p "Q_DEM=Remove Demucs ? [Y/N]: "
if /i "!Q_DEM!"=="Y" call :pip_remove demucs
if /i "!Q_DEM!"=="Y" call :logfile "Custom uninstall: pip uninstall demucs - code !ERRORLEVEL!"

set "Q_W2L="
set /p "Q_W2L=Remove Wav2Lip deps (new-basicsr/basicsr, facexlib, dlib) ? [Y/N]: "
if /i "!Q_W2L!"=="Y" call :pip_remove new-basicsr basicsr facexlib dlib dlib-bin
if /i "!Q_W2L!"=="Y" call :logfile "Custom uninstall: pip uninstall new-basicsr basicsr facexlib dlib dlib-bin - code !ERRORLEVEL!"

set "Q_PYA="
set /p "Q_PYA=Remove pyannote.audio (speaker diarization) ? [Y/N]: "
if /i "!Q_PYA!"=="Y" call :pip_remove pyannote.audio
if /i "!Q_PYA!"=="Y" call :logfile "Custom uninstall: pip uninstall pyannote.audio - code !ERRORLEVEL!"

set "Q_MIS="
set /p "Q_MIS=Remove pipeline utilities (yt-dlp, edge-tts, deep-translator, pydub, pyloudnorm, soundfile, sacremoses, sentencepiece) ? [Y/N]: "
if /i "!Q_MIS!"=="Y" call :pip_remove yt-dlp edge-tts deep-translator pydub pyloudnorm soundfile sacremoses sentencepiece
if /i "!Q_MIS!"=="Y" call :logfile "Custom uninstall: pip uninstall yt-dlp edge-tts deep-translator pydub pyloudnorm soundfile sacremoses sentencepiece - code !ERRORLEVEL!"

set "Q_MPV="
set /p "Q_MPV=Remove the integrated video player package (mpv / python-mpv) ? [Y/N]: "
if /i "!Q_MPV!"=="Y" call :pip_remove mpv python-mpv
if /i "!Q_MPV!"=="Y" call :logfile "Custom uninstall: pip uninstall mpv python-mpv - code !ERRORLEVEL!"

:uninst_custom_tools
echo.
echo  --- System-wide tools installed by setup ---
echo  ( remove only if you do not use them for other projects )
set "Q_PY="
set /p "Q_PY=Uninstall Python 3.11 and its per-user packages ? [Y/N]: "
if /i "!Q_PY!"=="Y" call :remove_python

set "Q_GIT="
set /p "Q_GIT=Uninstall Git for Windows ? [Y/N]: "
if /i "!Q_GIT!"=="Y" call :remove_git

set "Q_OLL="
set /p "Q_OLL=Uninstall Ollama (also wipes downloaded models, can be GB) ? [Y/N]: "
if /i "!Q_OLL!"=="Y" call :remove_ollama

goto uninst_done


:uninst_done
:: :remove_app left at most this script in the install folder, and only when
:: it runs from there. A plain (non-recursive) rmdir removes the folder only
:: when it is empty; otherwise the folder stays and the user is told.
if "%VTAI_REMOVE_INSTALL_DIR%"=="1" rmdir "%INSTALL_DIR%" 2>nul
if "%VTAI_REMOVE_INSTALL_DIR%"=="1" if exist "%INSTALL_DIR%" (
    echo.
    echo  [^^!] %INSTALL_DIR% still holds this uninstaller:
    echo      delete that folder by hand after closing this window.
    call :logfile "Remove application folder: only setup_windows.bat is left, to delete by hand"
)
call :logfile "RESULT: uninstall complete"
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
echo  Setup log (kept on purpose): %VTAI_SETUP_LOG%
echo.
pause
goto end


:: ============================================================================
:: SUBROUTINES - shared infrastructure
:: ============================================================================

:check_admin
set "IS_ADMIN=0"
net session >nul 2>&1
if not errorlevel 1 set "IS_ADMIN=1"
goto :eof


:print_banner
echo.
echo  ============================================
echo    %~1
echo  ============================================
echo.
goto :eof


:: %~1 = message. Appends "[time] message" to the setup log only: the
:: console output and the interactive prompts stay exactly as they are.
:: Always pass the message as ONE quoted argument. Inside the quotes
:: parentheses are safe; never use < > | ^ or a double quote in it.
:logfile
set "VTAI_LOG_RC=%ERRORLEVEL%"
if defined VTAI_CP "%VTAI_CHCP%" 65001 >nul
>>"%VTAI_SETUP_LOG%" echo [%TIME%] %~1
if defined VTAI_CP "%VTAI_CHCP%" %VTAI_CP% >nul
exit /b %VTAI_LOG_RC%


:: %~1 = mode name. Writes the session header and tells the user where the
:: log is. Runs append-only, so repeated runs keep their history.
:log_session
if defined VTAI_CP "%VTAI_CHCP%" 65001 >nul
>>"%VTAI_SETUP_LOG%" echo(
>>"%VTAI_SETUP_LOG%" echo ================================================================
>>"%VTAI_SETUP_LOG%" echo  Video Translator AI - Setup v%SCRIPT_VERSION% - %~1
>>"%VTAI_SETUP_LOG%" echo  Started: %DATE% %TIME%
>>"%VTAI_SETUP_LOG%" echo  User: %USERNAME%   Admin: %IS_ADMIN%   Arch: %PROCESSOR_ARCHITECTURE%
for /f "delims=" %%v in ('ver') do >>"%VTAI_SETUP_LOG%" echo  %%v
>>"%VTAI_SETUP_LOG%" echo  Script folder: %SCRIPT_DIR%
>>"%VTAI_SETUP_LOG%" echo ================================================================
if defined VTAI_CP "%VTAI_CHCP%" %VTAI_CP% >nul
echo  [*] Setup log: %VTAI_SETUP_LOG%
goto :eof


:validate_install
echo.
echo  [*] Validating installation...
if not defined PYTHON_EXE set "PYTHON_EXE=python"
"%PYTHON_EXE%" -c "import torch, faster_whisper, demucs, edge_tts, soundfile, numpy, requests" >nul 2>&1
if errorlevel 1 (
    echo.
    echo  ============================================
    echo    INSTALLATION INCOMPLETE
    echo  ============================================
    echo.
    echo   Some core modules failed to install.
    echo   Run setup_windows.bat again and choose
    echo   option [2] Repair / Update.
    echo.
    echo   Missing modules:
    call :check_module torch "torch (PyTorch)"
    call :check_module faster_whisper "faster-whisper"
    call :check_module demucs "demucs"
    call :check_module edge_tts "edge-tts"
    call :check_module soundfile "soundfile"
    call :check_module numpy "numpy"
    call :check_module requests "requests"
    echo.
    pause
    exit /b 1
)
echo  [+] All core modules importable.
call :logfile "Validation: core modules torch, faster_whisper, demucs, edge_tts, soundfile, numpy, requests import ok"
pushd "%INSTALL_DIR%" >nul 2>&1
"%PYTHON_EXE%" -c "import video_translator_gui" >nul 2>&1
set "APP_IMPORT_RC=%ERRORLEVEL%"
popd >nul 2>&1
if not "%APP_IMPORT_RC%"=="0" (
    echo.
    echo  ============================================
    echo    APPLICATION IMPORT FAILED
    echo  ============================================
    echo.
    echo   The installed application files are incomplete.
    echo   Run setup_windows.bat again and choose
    echo   option [2] Repair / Update.
    echo.
    call :logfile "Validation: the application does not import, code %APP_IMPORT_RC%"
    pause
    exit /b 1
)
echo  [+] Application importable.
call :logfile "Validation: application import ok"
exit /b 0


:check_module
"%PYTHON_EXE%" -c "import %~1" >nul 2>&1
if errorlevel 1 echo     - %~2
if errorlevel 1 call :logfile "Validation: missing module %~1"
goto :eof


:print_done
echo.
echo  ============================================
echo    %~1
echo  ============================================
echo.
echo   Launch "Video Translator AI" from the Desktop
echo   or run:
echo   python "%INSTALL_DIR%\video_translator_gui.py"
echo.
echo   NOTE: on first use, Whisper will download
echo   the selected model (150MB - 3GB depending on model).
echo.
echo   Setup log: %VTAI_SETUP_LOG%
echo.
pause
goto :eof


:pause_exit
echo.
pause
exit /b %~1


:reload_path
:: Reload PATH from registry into the current session.
:: Uses a temp file to bypass the 8191-char buffer limit of `for /f`.
:: NB: write via .NET WriteAllText with UTF8Encoding($false) to avoid the BOM
:: that PowerShell 5.1 default (Out-File -Encoding UTF8) prepends to the file.
:: The BOM would end up in the first PATH entry and break the first
:: `where` lookup on that entry.
powershell -NoProfile -Command "$p = [Environment]::GetEnvironmentVariable('PATH','Machine') + ';' + [Environment]::GetEnvironmentVariable('PATH','User'); [System.IO.File]::WriteAllText($env:TEMP + '\vtai_path.txt', $p, (New-Object System.Text.UTF8Encoding($false)))"
set "PATH="
if defined VTAI_CP "%VTAI_CHCP%" 65001 >nul
for /f "usebackq delims=" %%i in ("%TEMP%\vtai_path.txt") do set "PATH=!PATH!%%i"
if defined VTAI_CP "%VTAI_CHCP%" %VTAI_CP% >nul
del /Q "%TEMP%\vtai_path.txt" >nul 2>&1
goto :eof


:: ============================================================================
:: SUBROUTINES - preflight
:: ============================================================================

:preflight_arch
if /i "%VTAI_SKIP_PREFLIGHT%"=="1" exit /b 0
set "VTAI_ARCH=%PROCESSOR_ARCHITECTURE%"
if defined PROCESSOR_ARCHITEW6432 set "VTAI_ARCH=%PROCESSOR_ARCHITEW6432%"
if /i "%VTAI_ARCH%"=="AMD64" exit /b 0
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


:preflight_disk
if /i "%VTAI_SKIP_PREFLIGHT%"=="1" exit /b 0
set "INSTALL_DRIVE=%ProgramFiles:~0,1%"
set "FREE_GB=0"
for /f %%i in ('powershell -NoProfile -Command "[math]::Floor((Get-PSDrive '%INSTALL_DRIVE%').Free/1GB)"') do set "FREE_GB=%%i"
:: If PowerShell is unavailable or failed, FREE_GB stays at 0 -> we would show
:: a misleading "Found 0 GB free" error. Better to assume enough space and
:: let any real errors surface from later I/O operations.
if "%FREE_GB%"=="0" set "FREE_GB=999"
if %FREE_GB% GEQ 20 exit /b 0
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


:preflight_network
if /i "%VTAI_SKIP_PREFLIGHT%"=="1" exit /b 0
echo  [*] Checking Internet connection...
powershell -NoProfile -Command "try { [Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]::Tls12; $r=[Net.WebRequest]::Create('https://github.com'); $r.Method='HEAD'; $r.Timeout=5000; $r.GetResponse().Close(); exit 0 } catch { exit 1 }" >nul 2>&1
if not errorlevel 1 exit /b 0
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


:legacy_cleanup_current
if exist "%USER_LEGACY_DIR%" (
    echo  [*] Removing legacy per-user install: %USER_LEGACY_DIR%
    rmdir /S /Q "%USER_LEGACY_DIR%" 2>nul
)
if exist "%USER_LEGACY_WAV2LIP%" (
    echo  [*] Rimozione vecchi modelli Wav2Lip per-utente...
    rmdir /S /Q "%USER_LEGACY_WAV2LIP%" 2>nul
)
if exist "%USER_LEGACY_SHORTCUT%" del /Q "%USER_LEGACY_SHORTCUT%" 2>nul
goto :eof


:: ============================================================================
:: SUBROUTINES - install steps (shared between install + repair)
:: ============================================================================

:: %~1 = step label e.g. "1/6"
:step_python
echo [%~1] Checking Python...

:: Bug 1 fix: reject the Microsoft Store redirect stub
:: (\WindowsApps\python.exe is a 0-byte placeholder that re-installs Python
:: into a per-user sandbox -- contradicts the system-wide install we want
:: and triggers dozens of "is not on PATH" warnings on every pip install).
:: Strategy:
::   1. Prefer the official `py -3.11` launcher (always a real install).
::   2. Else walk `where python` candidates, skipping WindowsApps + 0-byte.
::   3. Else fall through to "install fresh" (Python 3.11.9 system-wide).
set "PYTHON_EXE="

py -3.11 -c "import sys" >nul 2>&1
if not errorlevel 1 (
    for /f "tokens=*" %%i in ('py -3.11 -c "import sys; print(sys.executable)" 2^>nul') do set "PYTHON_EXE=%%i"
)

if not defined PYTHON_EXE (
    for /f "tokens=*" %%i in ('where python 2^>nul') do (
        if not defined PYTHON_EXE call :_python_consider "%%i"
    )
)

if defined PYTHON_EXE goto step_python_found

echo  [^^!] No usable Python found ^(Microsoft Store stub does not count^).
echo      Downloading and installing Python 3.11.9 silently...
powershell -Command ^
    "$url = 'https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe';" ^
    "$out = $env:TEMP + '\python_installer.exe';" ^
    "Write-Host '     Downloading Python 3.11.9...';" ^
    "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12;" ^
    "$ProgressPreference = 'SilentlyContinue';" ^
    "Invoke-WebRequest -Uri $url -OutFile $out -UseBasicParsing;" ^
    "Write-Host '     Installing silently (this may take a minute)...';" ^
    "Start-Process -FilePath $out -ArgumentList '/quiet InstallAllUsers=1 PrependPath=1 Include_test=0 Include_doc=0' -Wait;" ^
    "Remove-Item $out -Force;" ^
    "Write-Host '  [+] Python 3.11 installed successfully.'"

if errorlevel 1 (
    echo  [^^!] Auto-install failed. Download manually from:
    echo      https://www.python.org/downloads/
    echo      Check "Add Python to PATH" during installation, then re-run this bat.
    call :logfile "Step 1/6 Python: FAILED - download or silent install of Python 3.11.9"
    exit /b 1
)
call :logfile "Step 1/6 Python: no usable Python found, installed Python 3.11.9 from python.org"
call :reload_path

:: After fresh install, point at the canonical install path explicitly so we
:: never resolve back to a Store stub still earlier on PATH.
if exist "%ProgramFiles%\Python311\python.exe" set "PYTHON_EXE=%ProgramFiles%\Python311\python.exe"

:step_python_found
if not defined PYTHON_EXE (
    for /f "tokens=*" %%i in ('where python 2^>nul') do (
        if not defined PYTHON_EXE call :_python_consider "%%i"
    )
)
if not defined PYTHON_EXE set "PYTHON_EXE=python"

for /f "tokens=*" %%i in ('"%PYTHON_EXE%" --version 2^>^&1') do set "PY_VER=%%i"
echo  [+] Found: !PY_VER! at !PYTHON_EXE!

"%PYTHON_EXE%" -c "import sys; sys.exit(0 if (3,10) <= sys.version_info[:2] <= (3,13) else 1)" >nul 2>&1
if not errorlevel 1 goto step_python_ok

echo  [X] Detected !PY_VER! is incompatible (need Python 3.10-3.13).
:: Short-circuit: if a previous run already installed Python 3.11.9
:: alongside at the standard ProgramFiles location, reuse it instead of
:: re-downloading 25 MB. Saves ~30s on every retry / re-install.
if exist "%ProgramFiles%\Python311\python.exe" (
    echo  [+] Python 3.11.9 already installed alongside at "%ProgramFiles%\Python311\python.exe", reusing.
    set "PYTHON_EXE=%ProgramFiles%\Python311\python.exe"
    goto step_python_post_install
)
echo  [*] Installing Python 3.11.9 alongside (without altering PATH)...
powershell -Command ^
    "$url = 'https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe';" ^
    "$out = $env:TEMP + '\python_installer.exe';" ^
    "Write-Host '     Downloading Python 3.11.9...';" ^
    "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12;" ^
    "$ProgressPreference = 'SilentlyContinue';" ^
    "Invoke-WebRequest -Uri $url -OutFile $out -UseBasicParsing;" ^
    "Write-Host '     Installing silently (this may take a minute)...';" ^
    "Start-Process -FilePath $out -ArgumentList '/quiet InstallAllUsers=1 Include_test=0 Include_doc=0' -Wait;" ^
    "Remove-Item $out -Force;" ^
    "Write-Host '  [+] Python 3.11 installed alongside.'"
if errorlevel 1 (
    echo  [^^!] Bundled Python 3.11.9 install failed. Aborting.
    echo      Install Python 3.10-3.13 manually from https://www.python.org/downloads/
    exit /b 1
)

set "PYTHON_EXE=%ProgramFiles%\Python311\python.exe"
if not exist "%PYTHON_EXE%" (
    echo  [^^!] Bundled Python 3.11.9 not found at "%PYTHON_EXE%" after install. Aborting.
    exit /b 1
)

:step_python_post_install
for /f "tokens=*" %%i in ('"%PYTHON_EXE%" --version 2^>^&1') do set "PY_VER=%%i"
echo  [+] Using bundled !PY_VER! at !PYTHON_EXE!

:step_python_ok
:: Bug 1 sanity: never proceed if PYTHON_EXE somehow still points at the
:: WindowsApps redirect stub -- pip would silently reroute installs into a
:: per-user sandbox and break system-wide setup.
echo(!PYTHON_EXE! | findstr /I /C:"WindowsApps" >nul
if not errorlevel 1 (
    echo  [X] PYTHON_EXE resolves to the Microsoft Store redirect:
    echo      !PYTHON_EXE!
    echo      That stub is a 0-byte placeholder; pip would install into a
    echo      per-user sandbox and emit "is not on PATH" warnings.
    echo.
    echo      To fix:
    echo        - Settings -^> Apps -^> Advanced app settings -^>
    echo          App execution aliases: disable "python.exe" + "python3.exe", OR
    echo        - Install Python 3.11.9 manually from
    echo          https://www.python.org/downloads/release/python-3119/
    echo      then re-run this script.
    call :logfile "Step 1/6 Python: FAILED - only the Microsoft Store stub was found"
    exit /b 1
)
call :logfile "Step 1/6 Python: ok - !PY_VER! at !PYTHON_EXE!"
exit /b 0


:: %~1 = candidate python.exe path. Sets PYTHON_EXE only if the candidate is a
::       real interpreter (not the WindowsApps stub, not a 0-byte file).
:: Used by :step_python to filter `where python` results -- see Bug 1.
:_python_consider
set "_CAND=%~1"
echo(!_CAND! | findstr /I /C:"WindowsApps" >nul
if not errorlevel 1 exit /b 0
if not exist "!_CAND!" exit /b 0
for %%S in ("!_CAND!") do if "%%~zS"=="0" exit /b 0
set "PYTHON_EXE=!_CAND!"
exit /b 0


:: Ask the updater (videotranslator\updater.py next to this script) for a
:: newer GitHub release. On success VTAI_NEW_SETUP holds the installer of that
:: release, verified and unpacked in %UPDATE_DIR%, and the caller hands over
:: from a top-level line (:repair_handover). Any failure leaves VTAI_NEW_SETUP
:: empty and the repair goes on with the local files: an update never blocks
:: a repair. Exit codes: 10 new release ready, 0 up to date, 2 cannot check,
:: 3 refused (checksum or archive).
:update_prepare
set "VTAI_NEW_SETUP="
echo.
echo  [*] Checking GitHub for a newer release...
if not exist "%SCRIPT_DIR%videotranslator\updater.py" (
    echo  [-] These files have no updater, skipping the check.
    call :logfile "Update check: skipped, the files next to the installer have no updater"
    goto :eof
)
pushd "%SCRIPT_DIR%" >nul 2>&1
if errorlevel 1 (
    call :logfile "Update check: skipped, cannot enter the installer folder"
    goto :eof
)
:: The trailing dot keeps the backslash of %SCRIPT_DIR% from escaping the quote.
"%PYTHON_EXE%" -m videotranslator.updater download --local "%SCRIPT_DIR%." --dest "%UPDATE_DIR%" --log "%VTAI_SETUP_LOG%"
set "UPDATE_RC=%ERRORLEVEL%"
popd >nul 2>&1
if "%UPDATE_RC%"=="10" goto update_prepare_ready
if "%UPDATE_RC%"=="0" (
    echo  [+] Already the latest release.
) else (
    echo  [-] No update installed, code %UPDATE_RC%: repairing with the local files.
)
call :logfile "Update check: no hand-over, code %UPDATE_RC%"
goto :eof

:update_prepare_ready
if exist "%UPDATE_DIR%\handoff.txt" set /p "VTAI_NEW_SETUP=" < "%UPDATE_DIR%\handoff.txt"
if not defined VTAI_NEW_SETUP goto update_prepare_lost
if not exist "!VTAI_NEW_SETUP!" goto update_prepare_lost
echo  [+] New release verified.
call :logfile "Update check: new release verified, ready to hand over"
goto :eof

:update_prepare_lost
set "VTAI_NEW_SETUP="
echo  [^^!] The new release is missing after the download: repairing with the local files.
call :logfile "Update check: hand-over file missing, repairing with the local files"
goto :eof


:: %~1 = step label
:step_copy_files
echo.
:: Refuse an incomplete source before changing the installed files, including
:: when repair runs directly from the installation folder.
for %%F in (requirements-core.txt requirements-optional.txt requirements-gpu-cu124.txt requirements-player.txt) do (
    if not exist "%SCRIPT_DIR%%%F" (
        echo  [ERROR] Missing %%F. Extract the complete release archive before running setup.
        call :logfile "Step 2/6 copy files: missing dependency profile %%F"
        exit /b 1
    )
)
echo [%~1] Preparing installation folder...
if not exist "%INSTALL_DIR%" mkdir "%INSTALL_DIR%"
echo  [+] Folder: %INSTALL_DIR%
:: Running from the install folder itself (the Start Menu update entry runs
:: the copy kept there): the files are already in place, and copying a file
:: onto itself fails. os.path.samefile sees through 8.3 names and junctions,
:: which a text comparison of the two paths would not.
"%PYTHON_EXE%" -c "import os,sys;sys.exit(0 if os.path.samefile(sys.argv[1],sys.argv[2]) else 1)" "%SCRIPT_DIR%." "%INSTALL_DIR%" >nul 2>&1
if not errorlevel 1 (
    echo  [+] Running from the install folder: the files are already in place.
    call :logfile "Step 2/6 copy files: running from the install folder, nothing to copy"
    exit /b 0
)
for %%F in (requirements-core.txt requirements-optional.txt requirements-gpu-cu124.txt requirements-player.txt) do (
    copy /Y "%SCRIPT_DIR%%%F" "%INSTALL_DIR%\%%F" >nul
    if errorlevel 1 (
        echo  [ERROR] Could not copy dependency profile %%F.
        call :logfile "Step 2/6 copy files: dependency profile %%F not copied"
        exit /b 1
    )
)

echo  [*] Copying script...
copy /Y "%SCRIPT_DIR%video_translator_gui.py" "%INSTALL_DIR%\video_translator_gui.py" >nul
if errorlevel 1 (
    echo  [^^!] Error copying script. Make sure video_translator_gui.py is in the same folder as this .bat
    call :logfile "Step 2/6 copy files: video_translator_gui.py not copied from %SCRIPT_DIR%"
    exit /b 1
)
echo  [+] Script copied.

if exist "%SCRIPT_DIR%videotranslator" (
    if not exist "%INSTALL_DIR%\videotranslator" mkdir "%INSTALL_DIR%\videotranslator"
    copy /Y "%SCRIPT_DIR%videotranslator\*.py" "%INSTALL_DIR%\videotranslator\" >nul
    if errorlevel 1 (
        echo  [^^!] Error copying Python package folder. Make sure videotranslator\*.py is next to this .bat
        call :logfile "Step 2/6 copy files: videotranslator package not copied from %SCRIPT_DIR%"
        exit /b 1
    )
    echo  [+] Python package copied.
)

if exist "%SCRIPT_DIR%assets" (
    if not exist "%INSTALL_DIR%\assets" mkdir "%INSTALL_DIR%\assets"
    copy /Y "%SCRIPT_DIR%assets\icon.ico" "%INSTALL_DIR%\assets\icon.ico" >nul 2>&1
    copy /Y "%SCRIPT_DIR%assets\icon.png" "%INSTALL_DIR%\assets\icon.png" >nul 2>&1
    copy /Y "%SCRIPT_DIR%assets\icon_256.png" "%INSTALL_DIR%\assets\icon_256.png" >nul 2>&1
    if exist "%SCRIPT_DIR%assets\fonts" (
        if not exist "%INSTALL_DIR%\assets\fonts" mkdir "%INSTALL_DIR%\assets\fonts"
        copy /Y "%SCRIPT_DIR%assets\fonts\*.*" "%INSTALL_DIR%\assets\fonts\" >nul 2>&1
    )
    echo  [+] Assets copied.
)
:: Keep a copy of this installer in the install folder: the Start Menu
:: "Update" entry runs it, even after the user deletes the download.
copy /Y "%SCRIPT_DIR%setup_windows.bat" "%INSTALL_DIR%\setup_windows.bat" >nul
if errorlevel 1 (
    echo  [^^!] Could not keep a copy of setup_windows.bat: the Start Menu update will not work.
    call :logfile "Step 2/6 copy files: setup_windows.bat NOT kept - the Start Menu update will not work"
) else (
    echo  [+] Installer kept for future updates.
)
call :logfile "Step 2/6 copy files: ok - %INSTALL_DIR%"
exit /b 0


:: %~1 = step label, %~2 = REPAIR_MODE flag (1 to skip optional VS Build Tools auto-install)
:step_install_deps
echo.
echo [%~1] Installing Python dependencies...
call :step_vc_runtime
echo  [*] Upgrading pip...
:: 2>nul suppresses the cosmetic "Impossibile trovare il file specificato."
:: that pip on Windows emits when cleaning up its own .exe during self-update
:: (file-lock workaround leaves a .deleteme that vanishes before the cleanup).
:: The upgrade itself succeeds; only the trailing cleanup whisper is hidden.
"%PYTHON_EXE%" -m pip install -c "%CORE_REQUIREMENTS%" -c "%OPTIONAL_REQUIREMENTS%" -c "%GPU_REQUIREMENTS%" --upgrade pip --quiet 2>nul

:: Requirements and constraints come from the shipped profiles. Constraints
:: also apply to every later optional install, so it cannot upgrade the core
:: ML stack outside the tested range. They do not install optional packages.

call :detect_torch_build
if "%TORCH_BUILD%"=="cpu" goto step_torch_cpu
echo  [*] Installing PyTorch cu124 + torchaudio + torchvision...
"%PYTHON_EXE%" -m pip install -c "%CORE_REQUIREMENTS%" -c "%OPTIONAL_REQUIREMENTS%" -c "%GPU_REQUIREMENTS%" -r "%GPU_REQUIREMENTS%" --quiet ^
  --index-url https://download.pytorch.org/whl/cu124
if errorlevel 1 (
    echo  [^^!] PyTorch cu124 failed, trying CPU version...
    call :logfile "Step 3/6 PyTorch: cu124 build failed, trying the CPU build"
    "%PYTHON_EXE%" -m pip install -c "%CORE_REQUIREMENTS%" -c "%OPTIONAL_REQUIREMENTS%" -c "%GPU_REQUIREMENTS%" -r "%GPU_REQUIREMENTS%" --quiet
    if errorlevel 1 call :logfile "Step 3/6 PyTorch: CPU build failed too"
) else (
    call :logfile "Step 3/6 PyTorch 2.6.0 cu124: ok"
)
goto step_torch_done

:step_torch_cpu
:: The Windows wheels of torch on PyPI are the CPU build. A CUDA build that
:: an earlier run installed already satisfies the profile and stays.
echo  [*] Installing PyTorch for the CPU + torchaudio + torchvision...
"%PYTHON_EXE%" -m pip install -c "%CORE_REQUIREMENTS%" -c "%OPTIONAL_REQUIREMENTS%" -c "%GPU_REQUIREMENTS%" -r "%GPU_REQUIREMENTS%" --quiet
if errorlevel 1 (
    echo  [^^!] PyTorch install failed.
    call :logfile "Step 3/6 PyTorch: CPU build FAILED"
) else (
    call :logfile "Step 3/6 PyTorch 2.6.0 CPU: ok"
)

:step_torch_done
echo  [*] Installing ctranslate2...
"%PYTHON_EXE%" -m pip install -c "%CORE_REQUIREMENTS%" -c "%OPTIONAL_REQUIREMENTS%" -c "%GPU_REQUIREMENTS%" ctranslate2 --quiet

echo  [*] Installing pipeline packages (faster-whisper, demucs, edge-tts, ...)...
"%PYTHON_EXE%" -m pip install -c "%CORE_REQUIREMENTS%" -c "%OPTIONAL_REQUIREMENTS%" -c "%GPU_REQUIREMENTS%" -r "%CORE_REQUIREMENTS%" pyannote.audio sentencepiece sacremoses silero-vad keyring --quiet
if errorlevel 1 (
    echo  [^^!] Error installing Python packages.
    call :logfile "Step 3/6 pipeline packages: FAILED - pip install of faster-whisper, demucs, edge-tts and the rest"
    exit /b 1
)
call :logfile "Step 3/6 pipeline packages: ok"

if "%TORCH_BUILD%"=="cpu" goto step_torch_checked
"%PYTHON_EXE%" -c "import torch,sys; sys.exit(0 if '+cu' in torch.__version__ else 1)" >nul 2>&1
if errorlevel 1 (
    echo  [^^!] PyTorch CUDA was downgraded by a dependency. Reinstalling cu124...
    call :logfile "Step 3/6 PyTorch: a dependency replaced the cu124 build, reinstalling cu124"
    "%PYTHON_EXE%" -m pip install -c "%CORE_REQUIREMENTS%" -c "%OPTIONAL_REQUIREMENTS%" -c "%GPU_REQUIREMENTS%" --upgrade --force-reinstall -r "%GPU_REQUIREMENTS%" --index-url https://download.pytorch.org/whl/cu124 --quiet
    if errorlevel 1 echo  [^^!] PyTorch cu124 reinstall failed - GPU acceleration may be unavailable.
    if errorlevel 1 call :logfile "Step 3/6 PyTorch: cu124 reinstall FAILED - GPU acceleration may be unavailable"
)
:step_torch_checked

echo  [*] Installing transformers ^(^>=4.40.0,^<5.1^)...
"%PYTHON_EXE%" -m pip install -c "%CORE_REQUIREMENTS%" -c "%OPTIONAL_REQUIREMENTS%" -c "%GPU_REQUIREMENTS%" transformers --quiet
if errorlevel 1 (
    echo  [^^!] transformers install failed.
    call :logfile "Step 3/6 transformers: FAILED"
    exit /b 1
)

"%PYTHON_EXE%" -m pip install -c "%CORE_REQUIREMENTS%" -c "%OPTIONAL_REQUIREMENTS%" -c "%GPU_REQUIREMENTS%" Cython setuptools wheel --quiet
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8
call :find_vcvarsall

echo  [*] Installing coqui-tts fork (voice cloning)...
"%PYTHON_EXE%" -m pip install -c "%CORE_REQUIREMENTS%" -c "%OPTIONAL_REQUIREMENTS%" -c "%GPU_REQUIREMENTS%" coqui-tts transformers --quiet 2>nul
if not errorlevel 1 goto step_tts_ok

"%PYTHON_EXE%" -m pip install -c "%CORE_REQUIREMENTS%" -c "%OPTIONAL_REQUIREMENTS%" -c "%GPU_REQUIREMENTS%" coqui-tts transformers --no-build-isolation --quiet 2>nul
if not errorlevel 1 goto step_tts_ok

if "%~2"=="1" (
    echo  [^^!] coqui-tts not installed and repair mode does not auto-install VS Build Tools.
    echo      Re-run setup_windows.bat install if you need voice cloning.
    call :logfile "Step 3/6 voice cloning coqui-tts: not installed - repair mode skips VS Build Tools"
    goto step_tts_end
)

echo  [*] VS C++ Build Tools not found - downloading and installing silently...
echo      (this may take 5-10 minutes, please wait)
call :logfile "Step 3/6 voice cloning: coqui-tts needs a compiler, installing VS C++ Build Tools"
powershell -Command ^
    "$url = 'https://aka.ms/vs/17/release/vs_BuildTools.exe';" ^
    "$out = $env:TEMP + '\vs_BuildTools.exe';" ^
    "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12;" ^
    "$ProgressPreference = 'SilentlyContinue';" ^
    "Invoke-WebRequest -Uri $url -OutFile $out -UseBasicParsing;" ^
    "Write-Host '     Installing VS C++ Build Tools (silent)...';" ^
    "Start-Process -FilePath $out -ArgumentList '--quiet --wait --norestart --nocache --installPath C:\BuildTools --add Microsoft.VisualStudio.Workload.VCTools --includeRecommended' -Wait;" ^
    "Remove-Item $out -Force;" ^
    "Write-Host '  [+] VS Build Tools installed.'"

if errorlevel 1 (
    echo  [^^!] VS Build Tools auto-install failed. Voice cloning skipped.
    call :logfile "Step 3/6 voice cloning: VS C++ Build Tools install FAILED"
    goto step_tts_failed
)

call :find_vcvarsall
"%PYTHON_EXE%" -m pip install -c "%CORE_REQUIREMENTS%" -c "%OPTIONAL_REQUIREMENTS%" -c "%GPU_REQUIREMENTS%" coqui-tts transformers --no-build-isolation --quiet 2>nul
if not errorlevel 1 goto step_tts_ok

:step_tts_failed
call :logfile "Step 3/6 voice cloning coqui-tts: NOT installed - everything else works"
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
echo  ^|     pip install coqui-tts "transformers<5.1"         ^|
echo  +------------------------------------------------------+
echo.
goto step_tts_end

:step_tts_ok
echo  [+] Coqui TTS installed successfully.
call :logfile "Step 3/6 voice cloning coqui-tts: ok"

:step_tts_end

call :step_wav2lip "%~2"
echo  [+] Python packages installed.
call :logfile "Step 3/6 Python packages: done"
exit /b 0


:: The CUDA build of PyTorch is a 2.5 GB download against 0.2 GB for the
:: CPU build, and it helps only on an NVIDIA GPU. The PCI vendor id 10DE
:: finds the card even before its driver is installed; nvidia-smi covers
:: the rest. Repair detects again: on a GPU added later the "+cu" check
:: after the pipeline packages replaces the CPU build.
:detect_torch_build
set "TORCH_BUILD=cu124"
where nvidia-smi >nul 2>&1
if not errorlevel 1 goto detect_torch_build_done
powershell -NoProfile -Command "if (Get-CimInstance Win32_VideoController | Where-Object { $_.PNPDeviceID -like 'PCI\VEN_10DE*' }) { exit 0 }; exit 1" >nul 2>&1
if not errorlevel 1 goto detect_torch_build_done
set "TORCH_BUILD=cpu"
:detect_torch_build_done
if "%TORCH_BUILD%"=="cu124" (
    echo  [+] NVIDIA GPU found: PyTorch with CUDA 12.4.
    call :logfile "Step 3/6 PyTorch: NVIDIA GPU found, CUDA 12.4 build"
) else (
    echo  [+] No NVIDIA GPU found: PyTorch for the CPU, 0.2 GB instead of 2.5 GB.
    call :logfile "Step 3/6 PyTorch: no NVIDIA GPU found, CPU build"
)
exit /b 0


:: PyTorch's DLLs (torch\lib\c10.dll) need the Microsoft Visual C++ 2015-2022
:: runtime: msvcp140.dll and vcruntime140_1.dll. A PC with games or Office has
:: it; a clean Windows does not, and `import torch` then fails with
:: WinError 126 (found on a fresh Windows 11 VM, 2026-09-27). Installed when
:: missing, in install and repair; never removed by the uninstaller, other
:: programs share it. The download goes to an administrators-only folder and
:: must carry a valid Microsoft Authenticode signature before it runs.
:step_vc_runtime
if exist "%SystemRoot%\System32\msvcp140.dll" if exist "%SystemRoot%\System32\vcruntime140_1.dll" (
    echo  [+] Microsoft Visual C++ runtime already installed.
    call :logfile "Step 3/6 Visual C++ runtime: already installed"
    exit /b 0
)
echo  [*] Installing the Microsoft Visual C++ runtime, needed by PyTorch...
call :logfile "Step 3/6 Visual C++ runtime: missing, downloading vc_redist.x64.exe from Microsoft"
set "VC_DIR=%INSTALL_DIR%\_downloads"
if not exist "%VC_DIR%" mkdir "%VC_DIR%"
powershell -NoProfile -Command ^
    "$url = 'https://aka.ms/vs/17/release/vc_redist.x64.exe';" ^
    "$out = '%VC_DIR%\vc_redist.x64.exe';" ^
    "try {" ^
    "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12;" ^
    "$ProgressPreference = 'SilentlyContinue';" ^
    "Invoke-WebRequest -Uri $url -OutFile $out -UseBasicParsing -ErrorAction Stop;" ^
    "$sig = Get-AuthenticodeSignature $out;" ^
    "if ($sig.Status -ne 'Valid' -or $sig.SignerCertificate.Subject -notlike '*O=Microsoft Corporation*') { Remove-Item $out -Force; exit 97 };" ^
    "$p = Start-Process -FilePath $out -ArgumentList '/install','/quiet','/norestart' -Wait -PassThru;" ^
    "Remove-Item $out -Force;" ^
    "exit $p.ExitCode" ^
    "} catch { exit 98 }"
set "VC_RC=%ERRORLEVEL%"
rmdir /S /Q "%VC_DIR%" 2>nul
:: 0 installed, 3010 installed (restart later), 1638 a newer one is present,
:: 97 not signed by Microsoft (refused), 98 download or launch failed
if "%VC_RC%"=="97" (
    echo  [^^!] The downloaded runtime is not signed by Microsoft: not installed.
    call :logfile "Step 3/6 Visual C++ runtime: REFUSED - the download has no valid Microsoft signature"
    goto step_vc_runtime_manual
)
if exist "%SystemRoot%\System32\msvcp140.dll" if exist "%SystemRoot%\System32\vcruntime140_1.dll" (
    echo  [+] Microsoft Visual C++ runtime installed.
    if "%VC_RC%"=="3010" echo      Windows asks for a restart: if PyTorch does not start, restart the PC.
    call :logfile "Step 3/6 Visual C++ runtime: ok, installer code %VC_RC%"
    exit /b 0
)
call :logfile "Step 3/6 Visual C++ runtime: install FAILED, code %VC_RC% (98 = download or launch failed)"
:step_vc_runtime_manual
echo      PyTorch will not start without it. Install it by hand from
echo      https://aka.ms/vs/17/release/vc_redist.x64.exe
echo      then run setup_windows.bat again and choose [2] Repair / Update.
exit /b 0


:: %~1 = REPAIR_MODE flag (currently unused, kept for symmetry / future)
:step_wav2lip
echo.
echo  [*] Installing Wav2Lip dependencies (new-basicsr, facexlib, dlib)...
echo      Note: using new-basicsr (maintained fork, ships pre-built wheel) instead
echo            of basicsr 1.4.2 -- original is abandoned and KeyError '__version__'
echo            on Python 3.13 (PEP 667 broke its setup.py exec/locals pattern).
echo            new-basicsr installs the same 'basicsr' module (drop-in import).

:: Use a temp file instead of `for /f` because cmd's `for /f ('cmd')` parsing
:: chokes when PYTHON_EXE contains spaces (C:\Program Files\...) AND the
:: inner Python code uses single quotes (f-strings). Live install on Win 10
:: showed `"C:\Program" non e' riconosciuto` followed by silent script exit.
"%PYTHON_EXE%" -c "import sys; print(str(sys.version_info.major)+str(sys.version_info.minor))" > "%TEMP%\vtai_pytag.txt" 2>nul
set "PY_TAG="
set /p "PY_TAG=" < "%TEMP%\vtai_pytag.txt"
del "%TEMP%\vtai_pytag.txt" >nul 2>&1
echo  [*] Python tag detected: cp%PY_TAG%

:: Bug 2 fix: the z-mahmud22 mirror does NOT publish a cp313 wheel
:: (HTTP 404). We keep entries only for python tags the mirror actually
:: ships, then fall back through PyPI -> dlib-bin -> "disabled" message.
set "DLIB_WHEEL_URL="
if "%PY_TAG%"=="39"  set "DLIB_WHEEL_URL=https://github.com/z-mahmud22/Dlib_Windows_Python3.x/raw/main/dlib-19.22.99-cp39-cp39-win_amd64.whl"
if "%PY_TAG%"=="310" set "DLIB_WHEEL_URL=https://github.com/z-mahmud22/Dlib_Windows_Python3.x/raw/main/dlib-19.22.99-cp310-cp310-win_amd64.whl"
if "%PY_TAG%"=="311" set "DLIB_WHEEL_URL=https://github.com/z-mahmud22/Dlib_Windows_Python3.x/raw/main/dlib-19.24.1-cp311-cp311-win_amd64.whl"
if "%PY_TAG%"=="312" set "DLIB_WHEEL_URL=https://github.com/z-mahmud22/Dlib_Windows_Python3.x/raw/main/dlib-19.24.99-cp312-cp312-win_amd64.whl"

"%PYTHON_EXE%" -c "import dlib" >nul 2>&1
if not errorlevel 1 (
    echo  [+] dlib already installed.
    call :logfile "Step 3/6 lip sync dlib: already installed"
    goto step_dlib_done
)

:: Cascade: mirror wheel -> PyPI sdist -> community dlib-bin -> disabled.
:: Each step has to run as a separate `if errorlevel` chain instead of nested
:: parens because the `set` inside ( ) wouldn't see the prior `errorlevel`.
set "_DLIB_OK="

if defined DLIB_WHEEL_URL (
    echo  [*] Trying pre-built dlib wheel for cp%PY_TAG% ^(mirror^)...
    "%PYTHON_EXE%" -m pip install -c "%CORE_REQUIREMENTS%" -c "%OPTIONAL_REQUIREMENTS%" -c "%GPU_REQUIREMENTS%" "%DLIB_WHEEL_URL%" --quiet
    if not errorlevel 1 set "_DLIB_OK=1"
)

if not defined _DLIB_OK (
    echo  [*] Mirror unavailable or absent. Trying official PyPI: pip install dlib ...
    "%PYTHON_EXE%" -m pip install -c "%CORE_REQUIREMENTS%" -c "%OPTIONAL_REQUIREMENTS%" -c "%GPU_REQUIREMENTS%" dlib --quiet
    if not errorlevel 1 set "_DLIB_OK=1"
)

if not defined _DLIB_OK (
    echo  [*] PyPI build failed. Trying community wheel: pip install dlib-bin ...
    "%PYTHON_EXE%" -m pip install -c "%CORE_REQUIREMENTS%" -c "%OPTIONAL_REQUIREMENTS%" -c "%GPU_REQUIREMENTS%" dlib-bin --quiet
    if not errorlevel 1 set "_DLIB_OK=1"
)

if defined _DLIB_OK (
    echo  [+] dlib installed.
    call :logfile "Step 3/6 lip sync dlib: ok"
) else (
    call :logfile "Step 3/6 lip sync dlib: NOT installed - lip sync disabled"
    echo.
    echo  +------------------------------------------------------+
    echo  ^|  Lip Sync disabled - dlib could not be installed.    ^|
    echo  ^|  Everything else works normally.                     ^|
    echo  ^|                                                      ^|
    echo  ^|  To enable Lip Sync manually, try one of:            ^|
    echo  ^|    pip install dlib                                  ^|
    echo  ^|    pip install dlib-bin                              ^|
    echo  ^|  or grab a pre-built wheel for your Python from:     ^|
    echo  ^|    github.com/z-mahmud22/Dlib_Windows_Python3.x      ^|
    echo  +------------------------------------------------------+
    echo.
)

:step_dlib_done
:: Use new-basicsr (maintained fork shipping a pre-built wheel) instead of
:: basicsr 1.4.2 -- abandoned 2022, fails to build on Python 3.13 with
:: KeyError '__version__' (PEP 667 broke its setup.py exec/locals pattern).
:: new-basicsr installs the SAME 'basicsr' module so all imports stay valid.
"%PYTHON_EXE%" -m pip install -c "%CORE_REQUIREMENTS%" -c "%OPTIONAL_REQUIREMENTS%" -c "%GPU_REQUIREMENTS%" new-basicsr facexlib --quiet
:: NB: parens inside `echo` inside an `if () else ()` block prematurely
:: close the else branch in cmd's parser. Use ^( ^) to escape, or drop them.
if errorlevel 1 (
    echo  [^^!] new-basicsr/facexlib install failed. Lip Sync may not work.
    call :logfile "Step 3/6 lip sync new-basicsr and facexlib: FAILED - lip sync may not work"
) else (
    echo  [+] new-basicsr ^(drop-in basicsr^) and facexlib installed.
    call :logfile "Step 3/6 lip sync new-basicsr and facexlib: ok"
)

if not exist "%WAV2LIP_DIR%" mkdir "%WAV2LIP_DIR%"
if exist "%WAV2LIP_REPO%\inference.py" goto step_wav2lip_repo_done

where git >nul 2>&1
if not errorlevel 1 goto step_wav2lip_clone

echo  [^^!] git not found. Downloading and installing Git for Windows silently...
powershell -Command ^
    "$url = 'https://github.com/git-for-windows/git/releases/download/v2.47.1.windows.1/Git-2.47.1-64-bit.exe';" ^
    "$out = $env:TEMP + '\git_installer.exe';" ^
    "Write-Host '     Downloading Git for Windows 2.47.1...';" ^
    "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12;" ^
    "$ProgressPreference = 'SilentlyContinue';" ^
    "Invoke-WebRequest -Uri $url -OutFile $out -UseBasicParsing;" ^
    "Write-Host '     Installing silently (this may take a minute)...';" ^
    "Start-Process -FilePath $out -ArgumentList '/VERYSILENT','/NORESTART','/NOCANCEL','/SP-','/SUPPRESSMSGBOXES','/COMPONENTS=icons,ext\reg\shellhere,assoc,assoc_sh' -Wait;" ^
    "Remove-Item $out -Force;" ^
    "Write-Host '  [+] Git for Windows installed.'"
if errorlevel 1 (
    echo  [^^!] Git auto-install failed. Install manually from https://git-scm.com/download/win
    call :logfile "Step 3/6 lip sync: Git for Windows install FAILED - Wav2Lip repo not cloned"
    goto step_wav2lip_repo_done
)
call :logfile "Step 3/6 lip sync: Git for Windows installed"

call :reload_path
timeout /t 2 /nobreak >nul

if exist "%ProgramFiles%\Git\cmd\git.exe" set "PATH=%ProgramFiles%\Git\cmd;%PATH%"
if exist "%ProgramFiles(x86)%\Git\cmd\git.exe" set "PATH=%ProgramFiles(x86)%\Git\cmd;%PATH%"
if exist "%LOCALAPPDATA%\Programs\Git\cmd\git.exe" set "PATH=%LOCALAPPDATA%\Programs\Git\cmd;%PATH%"

where git >nul 2>&1
if errorlevel 1 (
    echo  [^^!] git still not found after install. Lip Sync disabled.
    call :logfile "Step 3/6 lip sync: git still not found after install - lip sync disabled"
    goto step_wav2lip_repo_done
)

:step_wav2lip_clone
echo  [*] Cloning Wav2Lip repo...
git clone --depth 1 https://github.com/Rudrabha/Wav2Lip.git "%WAV2LIP_REPO%"
if errorlevel 1 (
    echo  [^^!] Wav2Lip clone failed. Lip Sync disabled.
    call :logfile "Step 3/6 lip sync: Wav2Lip repo clone FAILED - lip sync disabled"
) else (
    call :logfile "Step 3/6 lip sync: Wav2Lip repo cloned"
)

:step_wav2lip_repo_done
if exist "%WAV2LIP_MODEL%" (
    echo  [+] Wav2Lip GAN model already present.
    call :logfile "Step 3/6 lip sync model: already present"
    goto step_wav2lip_model_done
)

echo  [*] Downloading Wav2Lip GAN model ^(~416MB^)...

call :wav2lip_try_mirror "https://huggingface.co/Non-playing-Character/Wave2lip/resolve/main/wav2lip_gan.pth" "primary mirror (Non-playing-Character)"
if not errorlevel 1 goto step_wav2lip_sha

call :wav2lip_try_mirror "https://huggingface.co/Nekochu/Wav2Lip/resolve/main/wav2lip_gan.pth" "fallback mirror 1 (Nekochu)"
if not errorlevel 1 goto step_wav2lip_sha

call :wav2lip_try_mirror "https://huggingface.co/rippertnt/wav2lip/resolve/main/wav2lip_gan.pth" "fallback mirror 2 (rippertnt)"
if not errorlevel 1 goto step_wav2lip_sha

echo  [^^!] All Wav2Lip model mirrors failed. Lip Sync disabled.
echo  [^^!] Rest of the installation will continue normally.
call :logfile "Step 3/6 lip sync model: all 3 mirrors FAILED - lip sync disabled"
goto step_wav2lip_model_done

:step_wav2lip_sha
if not defined WAV2LIP_SHA256 (
    echo  [^^!] WAV2LIP_SHA256 not set - skipping integrity check.
    call :logfile "Step 3/6 lip sync model: no SHA256 to check against, integrity check skipped"
    goto step_wav2lip_model_done
)
set "GOT_SHA256="
for /f %%h in ('powershell -NoProfile -Command "(Get-FileHash '%WAV2LIP_MODEL%' -Algorithm SHA256).Hash.ToLower()"') do set "GOT_SHA256=%%h"
if /i "!GOT_SHA256!"=="!WAV2LIP_SHA256!" (
    echo  [+] Wav2Lip model SHA256 verified.
    call :logfile "Step 3/6 lip sync model: SHA256 verified"
    goto step_wav2lip_model_done
)
echo  [^^!] Wav2Lip model SHA256 mismatch. Expected !WAV2LIP_SHA256!, got !GOT_SHA256!.
call :logfile "Step 3/6 lip sync model: SHA256 MISMATCH - file deleted, lip sync disabled. Got !GOT_SHA256!"
del /Q "%WAV2LIP_MODEL%" >nul 2>&1

:step_wav2lip_model_done
exit /b 0


:: %~1 = URL, %~2 = label
:wav2lip_try_mirror
echo  [*] Trying %~2...
call :logfile "Step 3/6 lip sync model: downloading about 416 MB from %~2"
powershell -Command ^
    "try {" ^
    "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12;" ^
    "$ProgressPreference = 'SilentlyContinue';" ^
    "Invoke-WebRequest -Uri '%~1' -OutFile '%WAV2LIP_MODEL%' -UseBasicParsing -ErrorAction Stop;" ^
    "exit 0" ^
    "} catch { exit 1 }"
if errorlevel 1 goto wav2lip_try_fail
powershell -NoProfile -Command "if ((Get-Item '%WAV2LIP_MODEL%').Length -lt 100MB) { exit 1 } else { exit 0 }"
if not errorlevel 1 (
    echo  [+] Wav2Lip model downloaded.
    call :logfile "Step 3/6 lip sync model: downloaded from %~2"
    exit /b 0
)
:wav2lip_try_fail
echo  [^^!] %~2 failed.
call :logfile "Step 3/6 lip sync model: %~2 FAILED"
if exist "%WAV2LIP_MODEL%" del /Q "%WAV2LIP_MODEL%" >nul 2>&1
exit /b 1


:: %~1 = step label, %~2 = REPAIR_MODE flag (1 to skip if already installed)
:step_ffmpeg
echo.
echo [%~1] Installing ffmpeg...

if exist "%FFMPEG_DIR%\ffmpeg.exe" (
    echo  [+] ffmpeg already present, skipping download.
    call :logfile "Step 4/6 ffmpeg: already present"
    goto step_ffmpeg_path
)

powershell -Command "exit 0" >nul 2>&1
if errorlevel 1 (
    echo  [^^!] PowerShell not available. Download ffmpeg manually from:
    echo      https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip
    echo      and extract it to: %FFMPEG_DIR%
    goto step_ffmpeg_skip
)

echo  [*] Downloading ffmpeg (essentials build ~90MB)...
call :logfile "Step 4/6 ffmpeg: downloading the essentials build, about 90 MB"
if not exist "%FFMPEG_DIR%" mkdir "%FFMPEG_DIR%"

powershell -Command ^
    "$url = 'https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip';" ^
    "$zip = '%FFMPEG_DIR%\ffmpeg.zip';" ^
    "Write-Host '     Connecting...';" ^
    "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12;" ^
    "$ProgressPreference = 'SilentlyContinue';" ^
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
    echo  [^^!] ffmpeg download failed. You can download it manually from:
    echo      https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip
    echo      and extract ffmpeg.exe and ffprobe.exe to: %FFMPEG_DIR%
    call :logfile "Step 4/6 ffmpeg: download or extraction FAILED"
    goto step_ffmpeg_skip
)

:step_ffmpeg_path
set "PATH=%FFMPEG_DIR%;%PATH%"
powershell -Command ^
    "$p = [Environment]::GetEnvironmentVariable('PATH','Machine');" ^
    "if ($p -notlike '*%FFMPEG_DIR%*') {" ^
    "  [Environment]::SetEnvironmentVariable('PATH', $p + ';%FFMPEG_DIR%', 'Machine')" ^
    "}"
echo  [+] ffmpeg added to machine PATH.
call :logfile "Step 4/6 ffmpeg: ok - %FFMPEG_DIR% on the machine PATH"

powershell -Command ^
    "$p = [Environment]::GetEnvironmentVariable('PATH','User');" ^
    "if ($p -and $p -like '*%USERPROFILE%\VideoTranslatorAI\ffmpeg*') {" ^
    "  $new = ($p -split ';' | Where-Object { $_ -notlike '*%USERPROFILE%\VideoTranslatorAI\ffmpeg*' }) -join ';';" ^
    "  [Environment]::SetEnvironmentVariable('PATH', $new, 'User')" ^
    "}"
exit /b 0

:step_ffmpeg_skip
echo  [^^!] ffmpeg not installed - translation will not work without it.
call :logfile "Step 4/6 ffmpeg: NOT installed - translation will not work without it"
exit /b 0


:: %~1 = step label
:: Optional integrated video player: python-mpv (pip) plus a libmpv build in
:: %MPV_DIR%. Download, SHA256 checks, 7zr extraction and the load check all
:: run in Python (videotranslator\libmpv_runtime.py), so no PowerShell exit
:: code is involved. Any failure only disables the player: always exit 0.
:step_player
echo.
echo [%~1] Installing the integrated video player (optional)...
:: Use the same player profile as the command-line installation.
"%PYTHON_EXE%" -m pip install -c "%CORE_REQUIREMENTS%" -c "%OPTIONAL_REQUIREMENTS%" -c "%GPU_REQUIREMENTS%" -r "%PLAYER_REQUIREMENTS%" --quiet
if errorlevel 1 (
    call :logfile "Step 5/6 player: pip install of the mpv package FAILED"
    goto step_player_disabled
)
pushd "%INSTALL_DIR%" >nul 2>&1
if errorlevel 1 goto step_player_disabled
"%PYTHON_EXE%" -m videotranslator.libmpv_runtime install --dest "%MPV_DIR%"
set "MPV_RC=%ERRORLEVEL%"
popd >nul 2>&1
if not "%MPV_RC%"=="0" (
    call :logfile "Step 5/6 player: libmpv download or check FAILED, code %MPV_RC%"
    goto step_player_disabled
)
echo  [+] Integrated video player ready.
call :logfile "Step 5/6 player: ok - libmpv in %MPV_DIR%"
exit /b 0

:step_player_disabled
call :logfile "Step 5/6 player: disabled - the application works without it"
echo.
echo  ============================================
echo    Integrated player disabled - everything else works
echo  ============================================
echo.
echo   The application works without the player.
echo   To retry, run setup_windows.bat again and
echo   choose option [2] Repair / Update.
echo.
exit /b 0


:: Runs after :validate_install. A failed check only warns: the application
:: works without the integrated player.
:player_check
if not exist "%MPV_DIR%\mpv-2.dll" goto :eof
pushd "%INSTALL_DIR%" >nul 2>&1
if errorlevel 1 goto :eof
"%PYTHON_EXE%" -m videotranslator.libmpv_runtime check --dir "%MPV_DIR%" >nul 2>&1
set "MPV_CHECK_RC=%ERRORLEVEL%"
popd >nul 2>&1
if "%MPV_CHECK_RC%"=="0" (
    echo  [+] Integrated video player check passed.
    call :logfile "Player load check: ok"
) else (
    echo  [^^!] Integrated video player check failed, code %MPV_CHECK_RC%. The application works without it.
    call :logfile "Player load check: FAILED, code %MPV_CHECK_RC% - the application works without it"
)
goto :eof


:: %~1 = step label
:step_shortcut
echo.
echo [%~1] Creating Desktop shortcut...

:: Same temp-file trick as :step_wav2lip -- `for /f` chokes on PYTHON_EXE
:: with spaces + inner single quotes ('pythonw.exe').
"%PYTHON_EXE%" -c "import sys,os; print(os.path.join(os.path.dirname(sys.executable), 'pythonw.exe'))" > "%TEMP%\vtai_pythonw.txt" 2>nul
set "PYTHONW="
set /p "PYTHONW=" < "%TEMP%\vtai_pythonw.txt"
del "%TEMP%\vtai_pythonw.txt" >nul 2>&1

powershell -Command ^
    "$ws = New-Object -ComObject WScript.Shell;" ^
    "$s = $ws.CreateShortcut('%PUBLIC_SHORTCUT%');" ^
    "$s.TargetPath = '%PYTHONW%';" ^
    "$s.Arguments = [char]34 + '%INSTALL_DIR%\video_translator_gui.py' + [char]34;" ^
    "$s.WorkingDirectory = '%INSTALL_DIR%';" ^
    "$s.Description = 'Video Translator AI';" ^
    "if (Test-Path '%ICON_PATH%') { $s.IconLocation = '%ICON_PATH%' };" ^
    "$s.Save();"

if exist "%PUBLIC_SHORTCUT%" (
    echo  [+] Desktop shortcut created.
    call :logfile "Step 6/6 shortcut: ok - %PUBLIC_SHORTCUT%"
) else (
    echo  [^^!] Shortcut not created. You can launch the GUI with:
    echo      python "%INSTALL_DIR%\video_translator_gui.py"
    call :logfile "Step 6/6 shortcut: NOT created - pythonw was %PYTHONW%"
)

:: Start Menu folder: the application and "Update Video Translator AI". The
:: update entry runs the installer kept in %INSTALL_DIR% through the absolute
:: cmd.exe, as administrator: the documented LinkFlags bit RunAsUser (byte
:: 0x15 |= 0x20), set after the last Save() and only on a real shell link
:: header (size 0x4C). $Q is a double quote: cmd.exe would end the string.
powershell -NoProfile -Command ^
    "$Q = [char]34;" ^
    "$dir = '%START_MENU_DIR%';" ^
    "New-Item -ItemType Directory -Force -Path $dir | Out-Null;" ^
    "$ws = New-Object -ComObject WScript.Shell;" ^
    "$app = $ws.CreateShortcut($dir + '\Video Translator AI.lnk');" ^
    "$app.TargetPath = '%PYTHONW%';" ^
    "$app.Arguments = $Q + '%INSTALL_DIR%\video_translator_gui.py' + $Q;" ^
    "$app.WorkingDirectory = '%INSTALL_DIR%';" ^
    "$app.Description = 'Video Translator AI';" ^
    "if (Test-Path '%ICON_PATH%') { $app.IconLocation = '%ICON_PATH%' };" ^
    "$app.Save();" ^
    "$lnk = $dir + '\Update Video Translator AI.lnk';" ^
    "$upd = $ws.CreateShortcut($lnk);" ^
    "$upd.TargetPath = $env:ComSpec;" ^
    "$upd.Arguments = '/d /s /c ' + $Q + $Q + '%INSTALL_DIR%\setup_windows.bat' + $Q + ' update' + $Q;" ^
    "$upd.WorkingDirectory = '%INSTALL_DIR%';" ^
    "$upd.Description = 'Update Video Translator AI from GitHub';" ^
    "if (Test-Path '%ICON_PATH%') { $upd.IconLocation = '%ICON_PATH%' };" ^
    "$upd.Save();" ^
    "$b = [IO.File]::ReadAllBytes($lnk);" ^
    "if ($b.Length -gt 21 -and $b[0] -eq 0x4C) { $b[0x15] = $b[0x15] -bor 0x20; [IO.File]::WriteAllBytes($lnk, $b) }"

if exist "%START_MENU_DIR%\Update Video Translator AI.lnk" (
    echo  [+] Start Menu entries created: Video Translator AI, Update Video Translator AI.
    call :logfile "Step 6/6 Start Menu: ok - application and update entries"
) else (
    echo  [^^!] Start Menu entries not created.
    call :logfile "Step 6/6 Start Menu: NOT created"
)
exit /b 0


:find_vcvarsall
set "VCVARSALL="
if exist "C:\BuildTools\VC\Auxiliary\Build\vcvarsall.bat" (
    set "VCVARSALL=C:\BuildTools\VC\Auxiliary\Build\vcvarsall.bat"
    goto find_vcvarsall_activate
)
for %%d in (
    "C:\Program Files\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvarsall.bat"
    "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvarsall.bat"
    "C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvarsall.bat"
    "C:\Program Files (x86)\Microsoft Visual Studio\2019\BuildTools\VC\Auxiliary\Build\vcvarsall.bat"
) do (
    if exist %%d set "VCVARSALL=%%~d"
)
:find_vcvarsall_activate
if defined VCVARSALL (
    call "!VCVARSALL!" x64 >nul 2>&1
)
goto :eof


:: ============================================================================
:: SUBROUTINES - uninstall actions (ported verbatim from uninstall_windows.bat)
:: ============================================================================

:remove_app
echo  [*] Removing %INSTALL_DIR% ...
if not exist "%INSTALL_DIR%" (
    echo  [-] Not found, skipping.
    call :logfile "Remove application folder: not found, skipped"
    exit /b 0
)
:: This script may be the copy kept in the install folder (Start Menu update
:: entry), and cmd reads a batch file while it runs: removing it now would
:: stop the uninstall halfway. Everything else goes now; :uninst_done removes
:: the folder when it is empty.
:: The installer copy is kept only when it is this very script: a marker
:: written next to this script shows up in the install folder when both are
:: the same folder (8.3 names and junctions included). Run from elsewhere
:: (the release folder) it goes too, so the folder does not stay behind.
:: If the marker cannot be written, the copy is kept: never delete a running
:: script by mistake.
set "_KEEP_SELF=1"
set "_SELF_MARK=vtai_self_%RANDOM%%RANDOM%.tmp"
type nul > "%SCRIPT_DIR%%_SELF_MARK%" 2>nul
if exist "%SCRIPT_DIR%%_SELF_MARK%" (
    if not exist "%INSTALL_DIR%\%_SELF_MARK%" set "_KEEP_SELF="
    del /Q "%SCRIPT_DIR%%_SELF_MARK%" 2>nul
)
for /d %%D in ("%INSTALL_DIR%\*") do rmdir /S /Q "%%~D" 2>nul
for %%F in ("%INSTALL_DIR%\*") do if /i not "%%~nxF"=="setup_windows.bat" del /F /Q "%%~F" 2>nul
if not defined _KEEP_SELF del /F /Q "%INSTALL_DIR%\setup_windows.bat" 2>nul
set "VTAI_REMOVE_INSTALL_DIR=1"
set "_LEFT="
for /d %%D in ("%INSTALL_DIR%\*") do set "_LEFT=1"
for %%F in ("%INSTALL_DIR%\*") do if /i not "%%~nxF"=="setup_windows.bat" set "_LEFT=1"
if defined _LEFT (
    echo  [^^!] Some files could not be removed. Close any running Video Translator AI and retry.
    call :logfile "Remove application folder: PARTIAL - some files are in use, close the app and retry"
) else (
    echo  [+] Removed.
    call :logfile "Remove application folder: ok - %INSTALL_DIR%"
)
exit /b 0

:remove_shortcut_public
echo  [*] Removing the Desktop shortcut and the Start Menu entries ...
if exist "%PUBLIC_SHORTCUT%" (
    del /Q "%PUBLIC_SHORTCUT%" 2>nul
    echo  [+] Desktop shortcut removed.
    call :logfile "Remove Desktop shortcut: ok"
) else (
    echo  [-] Desktop shortcut not found, skipping.
    call :logfile "Remove Desktop shortcut: not found, skipped"
)
if exist "%START_MENU_DIR%" (
    rmdir /S /Q "%START_MENU_DIR%" 2>nul
    echo  [+] Start Menu entries removed.
    call :logfile "Remove Start Menu entries: ok"
) else (
    call :logfile "Remove Start Menu entries: not found, skipped"
)
exit /b 0

:remove_ffmpeg_path
echo  [*] Removing ffmpeg from machine PATH ...
call :logfile "Removing ffmpeg from the machine PATH"
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
call :logfile "Removing legacy per-user installs for all users"
for /d %%U in ("%SystemDrive%\Users\*") do (
    if exist "%%~U\VideoTranslatorAI" (
        echo      - %%~nxU : legacy app folder
        call :logfile "  user %%~nxU: removing legacy app folder"
        rmdir /S /Q "%%~U\VideoTranslatorAI" 2>nul
    )
    if exist "%%~U\.local\share\wav2lip" (
        echo      - %%~nxU : legacy wav2lip
        call :logfile "  user %%~nxU: removing legacy wav2lip"
        rmdir /S /Q "%%~U\.local\share\wav2lip" 2>nul
    )
    if exist "%%~U\Desktop\Video Translator AI.lnk" (
        echo      - %%~nxU : legacy shortcut
        call :logfile "  user %%~nxU: removing legacy shortcut"
        del /Q "%%~U\Desktop\Video Translator AI.lnk" 2>nul
    )
)
echo  [+] Done.
exit /b 0

:remove_legacy_current_user
echo  [*] Removing legacy per-user install for %USERNAME% ...
call :logfile "Removing legacy per-user install for %USERNAME%"
if exist "%USER_LEGACY_DIR%" rmdir /S /Q "%USER_LEGACY_DIR%" 2>nul
if exist "%USER_LEGACY_WAV2LIP%" rmdir /S /Q "%USER_LEGACY_WAV2LIP%" 2>nul
if exist "%USER_LEGACY_SHORTCUT%" del /Q "%USER_LEGACY_SHORTCUT%" 2>nul
echo  [+] Done.
exit /b 0

:remove_user_configs_all
echo  [*] Removing VTAI config and logs for all users ...
call :logfile "Removing config and logs for all users"
for /d %%U in ("%SystemDrive%\Users\*") do (
    if exist "%%~U\.videotranslatorai_config.json" (
        echo      - %%~nxU : legacy config file
        call :logfile "  user %%~nxU: removing legacy config file"
        del /Q "%%~U\.videotranslatorai_config.json" 2>nul
    )
    if exist "%%~U\AppData\Roaming\VideoTranslatorAI" (
        echo      - %%~nxU : config and logs
        call :logfile "  user %%~nxU: removing config and logs"
        rmdir /S /Q "%%~U\AppData\Roaming\VideoTranslatorAI" 2>nul
    )
)
echo  [+] Done.
exit /b 0

:remove_user_config_current
echo  [*] Removing VTAI config and logs for %USERNAME% ...
if exist "%USER_CONFIG%" del /Q "%USER_CONFIG%" 2>nul
if exist "%USER_APP_DATA%" (
    rmdir /S /Q "%USER_APP_DATA%" 2>nul
    echo  [+] Removed %USER_APP_DATA%
    call :logfile "Remove config and logs for %USERNAME%: ok - %USER_APP_DATA%"
) else (
    echo  [-] Not found.
    call :logfile "Remove config and logs for %USERNAME%: not found, skipped"
)
exit /b 0

:remove_user_caches_all
echo  [*] Removing model caches, runtimes and temp files for all users ...
call :logfile "Removing model caches, runtimes and temp files for all users"
for /d %%U in ("%SystemDrive%\Users\*") do (
    if exist "%%~U\.cache\huggingface\hub" (
        for /d %%M in ("%%~U\.cache\huggingface\hub\models--*") do (
            echo %%~nxM | findstr /i "whisper XTTS coqui wav2vec pyannote opus-mt" >nul && rmdir /S /Q "%%~M" 2>nul
        )
    )
    if exist "%%~U\AppData\Local\tts" (
        echo      - %%~nxU : XTTS cache
        call :logfile "  user %%~nxU: removing XTTS cache"
        rmdir /S /Q "%%~U\AppData\Local\tts" 2>nul
    )
    if exist "%%~U\AppData\Local\VideoTranslatorAI" (
        echo      - %%~nxU : player and JS runtimes
        call :logfile "  user %%~nxU: removing player and JS runtimes"
        rmdir /S /Q "%%~U\AppData\Local\VideoTranslatorAI" 2>nul
    )
    if exist "%%~U\AppData\Local\Temp\VideoTranslatorAI" (
        echo      - %%~nxU : temp files
        call :logfile "  user %%~nxU: removing temp files"
        rmdir /S /Q "%%~U\AppData\Local\Temp\VideoTranslatorAI" 2>nul
    )
)
echo  [+] Done.
exit /b 0

:remove_user_cache_current
echo  [*] Removing model caches, runtimes and temp files for %USERNAME% ...
call :logfile "Removing model caches, runtimes and temp files for %USERNAME%"
if exist "%USER_HF_CACHE%\hub" (
    for /d %%M in ("%USER_HF_CACHE%\hub\models--*") do (
        echo %%~nxM | findstr /i "whisper XTTS coqui wav2vec pyannote opus-mt" >nul && rmdir /S /Q "%%~M" 2>nul
    )
)
if exist "%USER_XTTS_CACHE%" rmdir /S /Q "%USER_XTTS_CACHE%" 2>nul
if exist "%USER_LOCAL_DATA%" rmdir /S /Q "%USER_LOCAL_DATA%" 2>nul
if exist "%USER_TEMP_DATA%" rmdir /S /Q "%USER_TEMP_DATA%" 2>nul
echo  [+] Done.
exit /b 0

:remove_saved_keys
:: Windows Credential Manager entries written through the keyring package
:: (service VideoTranslatorAI). Per Windows account: only the current user's
:: can be removed from here. Runs before the Python packages are removed.
echo  [*] Removing saved keys (HF token, ElevenLabs) for %USERNAME% ...
where python >nul 2>&1
if errorlevel 1 (
    echo  [^^!] python not found in PATH, skipping. Remove them in Credential Manager.
    call :logfile "Remove saved keys for %USERNAME%: SKIPPED - python not found, check Credential Manager"
    exit /b 0
)
if not defined PYTHON_EXE (
    for /f "tokens=*" %%i in ('where python 2^>nul') do (
        if not defined PYTHON_EXE set "PYTHON_EXE=%%i"
    )
)
if not defined PYTHON_EXE set "PYTHON_EXE=python"
"%PYTHON_EXE%" -c "import keyring;[print('  [+] removed '+u) for u in ('hf_token','elevenlabs_api_key') if keyring.get_password('VideoTranslatorAI',u) is not None and keyring.delete_password('VideoTranslatorAI',u) is None]" 2>nul
if errorlevel 1 echo  [^^!] Could not reach the keyring. Remove them in Credential Manager if present.
if errorlevel 1 (
    call :logfile "Remove saved keys for %USERNAME%: keyring NOT reachable, check Credential Manager"
) else (
    call :logfile "Remove saved keys for %USERNAME%: done"
)
echo  [+] Done.
exit /b 0

:remove_python_packages_all
echo  [*] Removing all Python AI packages ...
where python >nul 2>&1
if errorlevel 1 (
    echo  [^^!] python not found in PATH, skipping.
    call :logfile "Remove Python AI packages: SKIPPED - python not found"
    exit /b 0
)
if not defined PYTHON_EXE (
    for /f "tokens=*" %%i in ('where python 2^>nul') do (
        if not defined PYTHON_EXE set "PYTHON_EXE=%%i"
    )
)
if not defined PYTHON_EXE set "PYTHON_EXE=python"
:: Bug C fix: silero-vad, keyring and dlib-bin are installed by
:: :step_install_deps / :step_wav2lip but were missing here, leaving stale
:: packages after a "Remove all Python AI packages" uninstall.
call :pip_remove ^
    coqui-tts transformers ^
    torch torchaudio torchvision torchcodec ^
    faster-whisper ctranslate2 ^
    demucs ^
    new-basicsr basicsr facexlib dlib dlib-bin ^
    pyannote.audio ^
    silero-vad keyring ^
    mpv python-mpv ^
    yt-dlp edge-tts deep-translator pydub pyloudnorm soundfile sacremoses sentencepiece
call :logfile "Remove Python AI packages: pip uninstall finished, code %ERRORLEVEL%"
echo  [+] Done.
exit /b 0

:: %* = distributions to remove. Only the installed ones reach pip: the
:: lists keep legacy names (basicsr, python-mpv, dlib-bin) and pip printed
:: "WARNING: Skipping basicsr as it is not installed" for each missing one.
:: Names compare as pip normalizes them. ERRORLEVEL is pip's exit code, 0
:: when none of them is installed.
:pip_remove
"%PYTHON_EXE%" -c "import re, subprocess, sys; from importlib import metadata; norm = lambda name: re.sub(r'[-_.]+', '-', name).lower(); have = {norm(dist.metadata.get('Name') or '') for dist in metadata.distributions()}; present = [name for name in sys.argv[1:] if norm(name) in have]; sys.exit(subprocess.call([sys.executable, '-m', 'pip', 'uninstall', '-y', *present]) if present else 0)" %*
exit /b

:remove_python
echo  [*] Uninstalling Python 3.11 ...
call :logfile "Uninstalling Python 3.11"
:: Bug B fix: when Python 3.11 was originally installed via the Microsoft
:: Store stub (Bug 1), no entry exists in the Uninstall registry. The PS
:: block now exits 2 in that case so we can fall back to winget, then to a
:: forced rmdir of any leftover %ProgramFiles%\Python311.
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
    "$W = '[' + [char]33 + ']';" ^
    "$roots = 'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall','HKLM:\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall','HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall';" ^
    "$found = foreach ($r in $roots) { if (Test-Path $r) { Get-ChildItem $r -ErrorAction SilentlyContinue | ForEach-Object { Get-ItemProperty $_.PSPath -ErrorAction SilentlyContinue } | Where-Object { $_.DisplayName -match '^Python 3\.11' -and ($_.QuietUninstallString -or $_.UninstallString) } } };" ^
    "if (-not $found) { Write-Host '  [-] Python 3.11 not found in uninstall registry.'; exit 2 };" ^
    "foreach ($u in $found) {" ^
    "    Write-Host ('  [*] ' + $u.DisplayName);" ^
    "    $cmd = if ($u.QuietUninstallString) { $u.QuietUninstallString } else { $u.UninstallString + ' /quiet' };" ^
    "    try { Start-Process -FilePath 'cmd.exe' -ArgumentList '/c', $cmd -Wait -NoNewWindow; Write-Host '  [+] Done.' }" ^
    "    catch { Write-Host ('  ' + $W + ' Failed: ' + $_.Exception.Message) }" ^
    "}"

if errorlevel 2 (
    where winget >nul 2>&1
    if not errorlevel 1 (
        echo  [*] Trying winget fallback for Python 3.11 ...
        winget uninstall --id Python.Python.3.11 --silent --accept-source-agreements
    ) else (
        echo  [-] winget unavailable, skipping winget fallback.
    )
)

if exist "%ProgramFiles%\Python311" (
    echo  [*] Removing leftover folder "%ProgramFiles%\Python311" ...
    rmdir /S /Q "%ProgramFiles%\Python311" 2>nul
    if exist "%ProgramFiles%\Python311" (
        echo  [^^!] Could not remove leftover folder. Please remove it manually.
        call :logfile "Uninstall Python 3.11: leftover folder could NOT be removed"
    ) else (
        echo  [+] Leftover folder removed.
        call :logfile "Uninstall Python 3.11: leftover folder removed"
    )
)
call :remove_python_user_site
exit /b 0

:: pip run without admin rights (the app installs what it misses that way)
:: writes to %APPDATA%\Python\Python311, which the Python uninstaller leaves:
:: the next Python 3.11 loaded those packages again and pip reported
:: conflicts. Every CPython 3.11 of this account shares the folder, so it
:: goes only when none is left.
:remove_python_user_site
set "PY311_USER_SITE=%APPDATA%\Python\Python311"
if not exist "%PY311_USER_SITE%" exit /b 0
call :python311_present
if not errorlevel 1 (
    echo  [-] Another Python 3.11 is still installed: keeping its per-user packages in "%PY311_USER_SITE%".
    call :logfile "Uninstall Python 3.11: per-user packages kept, another Python 3.11 is still installed"
    exit /b 0
)
echo  [*] Removing the per-user packages in "%PY311_USER_SITE%" ...
rmdir /S /Q "%PY311_USER_SITE%" 2>nul
if exist "%PY311_USER_SITE%" (
    echo  [^^!] Could not remove "%PY311_USER_SITE%". Please remove it manually.
    call :logfile "Uninstall Python 3.11: per-user packages could NOT be removed"
) else (
    echo  [+] Per-user packages removed.
    call :logfile "Uninstall Python 3.11: per-user packages removed"
)
exit /b 0

:: Exit code 0 while a Python 3.11 is installed: registered for this account
:: or for the machine (PEP 514), or found on PATH (conda, pyenv, ...).
:python311_present
powershell -NoProfile -Command "foreach ($k in 'HKCU:\Software\Python\PythonCore\3.11\InstallPath','HKLM:\Software\Python\PythonCore\3.11\InstallPath','HKLM:\Software\WOW6432Node\Python\PythonCore\3.11\InstallPath') { $d = (Get-ItemProperty -LiteralPath $k -ErrorAction SilentlyContinue).'(default)'; if ($d -and (Test-Path -LiteralPath (Join-Path $d 'python.exe'))) { exit 0 } }; exit 1" >nul 2>&1
if not errorlevel 1 exit /b 0
for /f "delims=" %%P in ('where python 2^>nul') do (
    "%%P" -c "import sys; sys.exit(0 if sys.version_info[:2] == (3, 11) else 1)" >nul 2>&1
    if not errorlevel 1 exit /b 0
)
exit /b 1

:remove_git
echo  [*] Uninstalling Git for Windows ...
call :logfile "Uninstalling Git for Windows"
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
    "$W = '[' + [char]33 + ']';" ^
    "$roots = 'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall','HKLM:\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall','HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall';" ^
    "$found = foreach ($r in $roots) { if (Test-Path $r) { Get-ChildItem $r -ErrorAction SilentlyContinue | ForEach-Object { Get-ItemProperty $_.PSPath -ErrorAction SilentlyContinue } | Where-Object { $_.DisplayName -match '^Git( |$)' -and $_.DisplayName -notmatch 'LFS|Extensions' -and $_.UninstallString } } };" ^
    "if (-not $found) { Write-Host '  [-] Git for Windows not found.'; exit 0 };" ^
    "foreach ($u in $found) {" ^
    "    Write-Host ('  [*] ' + $u.DisplayName);" ^
    "    $exe = $u.UninstallString.Trim([char]34).Trim();" ^
    "    if (Test-Path $exe) {" ^
    "        try { Start-Process -FilePath $exe -ArgumentList '/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART' -Wait; Write-Host '  [+] Done.' }" ^
    "        catch { Write-Host ('  ' + $W + ' Failed: ' + $_.Exception.Message) }" ^
    "    } else { Write-Host ('  ' + $W + ' Uninstaller not found at ' + $exe) }" ^
    "}"
exit /b 0

:remove_ollama
echo  [*] Uninstalling Ollama ...
call :logfile "Uninstalling Ollama"
:: Stop running daemon and tray app first so the uninstaller can replace files.
:: Different Ollama Windows builds use different process names --try them all.
taskkill /F /IM ollama.exe       >nul 2>&1
taskkill /F /IM ollama_app.exe   >nul 2>&1
taskkill /F /IM "Ollama.exe"     >nul 2>&1
taskkill /F /IM "Ollama Helper.exe" >nul 2>&1
:: Run the registered uninstaller fully silent. Ollama Windows uses Squirrel
:: (NOT NSIS) -- the registry UninstallString points at Update.exe with the
:: --uninstall flag. We append `-s` for Squirrel-silent. Other apps that
:: happen to match "^Ollama" get the standard NSIS /S fallback.
:: Per-user install lands in HKCU, so we scan HKLM + HKCU + WOW6432Node.
:: Also kill any stray Update.exe so the new spawn isn't blocked.
taskkill /F /IM Update.exe       >nul 2>&1
:: Bug A fix: cmd.exe does NOT honour `\"` as an escape -- the `"` closes
:: the cmd-level string, PowerShell receives a truncated command, and you
:: get `MissingEndCurlyBrace`. Use [char]34 (assigned to $Q, same trick as
:: :remove_git) and parse UninstallString character-by-character with
:: StartsWith / IndexOf / Substring so no quote ever appears in the regex.
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
    "$W = '[' + [char]33 + ']';" ^
    "$Q = [char]34;" ^
    "$roots = 'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall','HKLM:\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall','HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall';" ^
    "$found = foreach ($r in $roots) { if (Test-Path $r) { Get-ChildItem $r -ErrorAction SilentlyContinue | ForEach-Object { Get-ItemProperty $_.PSPath -ErrorAction SilentlyContinue } | Where-Object { $_.DisplayName -match '^Ollama' -and $_.UninstallString } } };" ^
    "if (-not $found) { Write-Host '  [-] Ollama not found in uninstall registry.' } else {" ^
    "  foreach ($u in $found) {" ^
    "    Write-Host ('  [*] ' + $u.DisplayName);" ^
    "    $raw = $u.UninstallString.Trim();" ^
    "    if ($raw.StartsWith($Q)) {" ^
    "      $end = $raw.IndexOf($Q, 1);" ^
    "      if ($end -gt 0) { $exe = $raw.Substring(1, $end - 1); $extra = $raw.Substring($end + 1).Trim() }" ^
    "      else { $exe = $raw.Trim($Q); $extra = '' }" ^
    "    } else {" ^
    "      $sp = $raw.IndexOf(' ');" ^
    "      if ($sp -gt 0) { $exe = $raw.Substring(0, $sp); $extra = $raw.Substring($sp + 1).Trim() }" ^
    "      else { $exe = $raw; $extra = '' }" ^
    "    };" ^
    "    if (-not (Test-Path $exe)) { Write-Host ('  ' + $W + ' Uninstaller not found at ' + $exe); continue };" ^
    "    if ($exe -match 'Update\.exe$') { $argsArr = @('--uninstall','-s') }" ^
    "    elseif ($extra -match '--uninstall') { $argsArr = ($extra -split '\s+') + @('-s') }" ^
    "    else { $argsArr = @('/S') };" ^
    "    try { Start-Process -FilePath $exe -ArgumentList $argsArr -Wait -WindowStyle Hidden; Write-Host '  [+] Done.' }" ^
    "    catch { Write-Host ('  ' + $W + ' Failed: ' + $_.Exception.Message) }" ^
    "  }" ^
    "}"
:: Force-remove leftover directories for every Windows user (binaries, model cache).
:: The model cache (.ollama\models) is the bulk of disk usage --multi-GB per user.
echo  [*] Removing Ollama leftover directories for all users ...
for /f "delims=" %%U in ('dir /b /a:d "%SystemDrive%\Users" 2^>nul') do (
    if exist "%SystemDrive%\Users\%%U\.ollama" rmdir /S /Q "%SystemDrive%\Users\%%U\.ollama" >nul 2>&1
    if exist "%SystemDrive%\Users\%%U\AppData\Local\Programs\Ollama" rmdir /S /Q "%SystemDrive%\Users\%%U\AppData\Local\Programs\Ollama" >nul 2>&1
    if exist "%SystemDrive%\Users\%%U\AppData\Local\Ollama" rmdir /S /Q "%SystemDrive%\Users\%%U\AppData\Local\Ollama" >nul 2>&1
)
echo  [+] Done.
exit /b 0


:end
endlocal
exit /b 0
