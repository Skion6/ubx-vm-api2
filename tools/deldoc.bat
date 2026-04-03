@echo off
echo Stopping all Docker containers...
FOR /F "tokens=*" %%i IN ('docker ps -aq') DO docker stop %%i

echo Removing all Docker artifacts...
docker system prune -a --volumes -f

echo Docker cleanup complete.
pause
