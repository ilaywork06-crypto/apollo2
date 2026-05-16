@echo off
echo Updating Apollo...
git pull
echo.
echo Rebuilding Docker images...
cd docker
docker-compose down
docker-compose build --no-cache
echo.
echo Update complete! Run start.bat to start the app.
pause