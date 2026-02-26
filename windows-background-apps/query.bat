@echo off
setlocal

set "allowed=True"

:: Проверяем пользовательскую настройку
reg query "HKCU\Software\Microsoft\Windows\CurrentVersion\BackgroundAccessApplications" /v "GlobalUserDisabled" 2>nul | findstr /r "0x1$" >nul && set "allowed=False"

:: Проверяем политику (если задана)
reg query "HKLM\Software\Policies\Microsoft\Windows\AppPrivacy" /v "LetAppsRunInBackground" 2>nul | findstr /r "0x2$" >nul && set "allowed=False"
reg query "HKLM\Software\Policies\Microsoft\Windows\AppPrivacy" /v "LetAppsRunInBackground" 2>nul | findstr /r "0x1$" >nul && set "allowed=True"

echo %allowed%
exit /b 0