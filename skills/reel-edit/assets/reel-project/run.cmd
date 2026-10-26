@echo off
rem Windows launcher for run.sh: finds Git Bash (installs Git for Windows with winget if it's missing) and runs
rem   run.cmd setup        run.cmd transcribe public/recordings/take.mp4        run.cmd doctor
rem From PowerShell:  cd ~\Videos\reels; .\run.cmd setup      (setup.cmd does the same on a double-click)
setlocal
cd /d "%~dp0"
call :findbash
if not defined GITBASH (
  echo Git Bash is needed to run Video Studio's setup. Installing Git for Windows with winget...
  winget install --id Git.Git -e --silent --accept-package-agreements --accept-source-agreements
  call :findbash
)
if not defined GITBASH (
  echo FAIL: could not find or install Git Bash. Install Git for Windows from https://git-scm.com/download/win
  echo then run this again.
  set "RC=1"
  goto :end
)
"%GITBASH%" run.sh %*
set "RC=%ERRORLEVEL%"
:end
if defined VS_PAUSE if not defined CI pause
exit /b %RC%

:findbash
set "GITBASH="
for %%P in ("%ProgramFiles%\Git\bin\bash.exe" "%ProgramW6432%\Git\bin\bash.exe" "%ProgramFiles(x86)%\Git\bin\bash.exe" "%LOCALAPPDATA%\Programs\Git\bin\bash.exe") do (
  if not defined GITBASH if exist "%%~P" set "GITBASH=%%~P"
)
exit /b 0
