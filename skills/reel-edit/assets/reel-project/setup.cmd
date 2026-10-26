@echo off
rem Windows: double-click this file to set up the project (the same as "bash run.sh setup" on macOS and Linux).
rem It installs what's missing (Git Bash, ffmpeg, Node, Python, the speech model) and ends with "All set."
set "VS_PAUSE=1"
call "%~dp0run.cmd" setup
