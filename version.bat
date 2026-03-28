@echo off
echo Updating FundCompare...

cd /d "%~dp0"

:: Save community.json before pull
if exist community.json (
    copy community.json community_backup.json
)

:: Discard all local changes and pull
git checkout .
git pull

:: Restore community.json
if exist community_backup.json (
    copy community_backup.json community.json
    del community_backup.json
)

echo Update complete!
pause