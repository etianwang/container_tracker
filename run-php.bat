@echo off
php -d max_execution_time=70 -S 127.0.0.1:8080 -t "%~dp0"
