@echo off
setlocal EnableDelayedExpansion
chcp 65001 >nul
title SIA Simulation - Установка и запуск

echo ======================================================================
echo           SIA Simulation Workbench - Автоматическая установка
echo ======================================================================
echo.

:: 1. Выбор папки установки
set "DEFAULT_DIR=%USERPROFILE%\SIA_Simulation"
echo Куда установить симуляцию?
echo [Нажмите Enter для пути по умолчанию: %DEFAULT_DIR%]
set /p "TARGET_DIR=Путь: "
if "!TARGET_DIR!"=="" set "TARGET_DIR=%DEFAULT_DIR%"

:: Создаем папку если её нет
if not exist "!TARGET_DIR!" (
    mkdir "!TARGET_DIR!" 2>nul
)

echo.
echo [1/4] Скачивание исходного кода проекта в !TARGET_DIR!...

:: 2. Скачивание проекта (Git или ZIP через PowerShell)
where git >nul 2>nul
if !ERRORLEVEL! EQU 0 (
    echo Использован Git для загрузки...
    if exist "!TARGET_DIR!\.git" (
        cd /d "!TARGET_DIR!"
        git pull
    ) else (
        git clone https://github.com/dzentec/SIA_SIM.git "!TARGET_DIR!"
    )
) else (
    echo Git не найден, скачивание ZIP архива через PowerShell...
    powershell -NoProfile -ExecutionPolicy Bypass -Command ^
        "$zip = Join-Path $env:TEMP 'sia_sim.zip';" ^
        "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12;" ^
        "Write-Host 'Загрузка архива...';" ^
        "Invoke-WebRequest -Uri 'https://github.com/dzentec/SIA_SIM/archive/refs/heads/main.zip' -OutFile $zip;" ^
        "Write-Host 'Распаковка...';" ^
        "Expand-Archive -Path $zip -DestinationPath $env:TEMP\sia_extract -Force;" ^
        "Copy-Item -Path $env:TEMP\sia_extract\SIA_SIM-main\* -Destination '!TARGET_DIR!' -Recurse -Force;" ^
        "Remove-Item $zip -Force; Remove-Item $env:TEMP\sia_extract -Recurse -Force;"
)

cd /d "!TARGET_DIR!"

if not exist "!TARGET_DIR!\pyproject.toml" (
    echo.
    echo [ОШИБКА] Не удалось загрузить файлы проекта в !TARGET_DIR!.
    pause
    exit /b 1
)

:: 3. Проверка / установка uv и зависимостей
echo.
echo [2/4] Проверка менеджера пакетов uv...
set "PATH=%USERPROFILE%\.local\bin;%USERPROFILE%\.cargo\bin;%PATH%"
where uv >nul 2>nul
if !ERRORLEVEL! NEQ 0 (
    echo Установка uv (автономный менеджер Python)...
    powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
    set "PATH=%USERPROFILE%\.local\bin;%USERPROFILE%\.cargo\bin;%PATH%"
)

echo.
echo [3/4] Установка Python 3.12 и зависимостей симуляции...
uv sync --quiet

:: 4. Создание файла start_workbench.bat прямо в папке проекта
echo @echo off > "!TARGET_DIR!\start_workbench.bat"
echo title SIA Simulation Workbench >> "!TARGET_DIR!\start_workbench.bat"
echo cd /d "%%~dp0" >> "!TARGET_DIR!\start_workbench.bat"
echo start "" "http://localhost:8050" >> "!TARGET_DIR!\start_workbench.bat"
echo if exist ".venv\Scripts\python.exe" ( >> "!TARGET_DIR!\start_workbench.bat"
echo     ".venv\Scripts\python.exe" -m sia_sim.workbench.server --port 8050 >> "!TARGET_DIR!\start_workbench.bat"
echo ) else ( >> "!TARGET_DIR!\start_workbench.bat"
echo     uv run sia-sim --workbench --port 8050 >> "!TARGET_DIR!\start_workbench.bat"
echo ) >> "!TARGET_DIR!\start_workbench.bat"
echo pause >> "!TARGET_DIR!\start_workbench.bat"

:: 5. Создание ярлыка на Рабочем столе через PowerShell
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
    "$ws = New-Object -ComObject WScript.Shell;" ^
    "$desktop = [Environment]::GetFolderPath('Desktop');" ^
    "$s = $ws.CreateShortcut((Join-Path $desktop 'SIA Simulation Workbench.lnk'));" ^
    "$s.TargetPath = '!TARGET_DIR!\start_workbench.bat';" ^
    "$s.WorkingDirectory = '!TARGET_DIR!';" ^
    "$s.Save();"

echo.
echo [4/4] Готово!
echo Создан файл запуска: "!TARGET_DIR!\start_workbench.bat"
echo Создан ярлык на Рабочем столе: "SIA Simulation Workbench"
echo.
echo Запуск симуляции...
start "" "http://localhost:8050"
"!TARGET_DIR!\.venv\Scripts\python.exe" -m sia_sim.workbench.server --port 8050

pause
