@echo off
REM Regenerate Gmail drafts from an existing outreach\people.json
REM Usage: make_drafts.bat "Company Name" "Role Title"
REM        add a 3rd arg "net" for networking mode (companies you did NOT apply to)
cd /d C:\JobRadar
if /I "%~3"=="net" (
    python outreach\outreach.py "%~1" "%~2" --people outreach\people.json --drafts --networking
) else (
    python outreach\outreach.py "%~1" "%~2" --people outreach\people.json --drafts
)
echo.
pause
