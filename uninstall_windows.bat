@echo off
:: ============================================================================
::  Backward-compat stub.
::  Real logic lives in setup_windows.bat (unified installer/repair/uninstaller).
::  If you rename or move this file, update setup_windows.bat as well.
:: ============================================================================
"%~dp0setup_windows.bat" uninstall %*
exit /b %errorlevel%
