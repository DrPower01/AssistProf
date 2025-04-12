@echo off
echo Installing pre-compiled mysqlclient wheel...
pip uninstall -y mysqlclient
pip install --only-binary :all: mysqlclient
echo If the above fails, please install Microsoft C++ Build Tools
echo from https://visualstudio.microsoft.com/visual-cpp-build-tools/
echo.
echo Alternatively, you can use the mysql-connector-python package 
echo which is already installed and doesn't require compilation.
