@echo off
setlocal
chcp 65001 >nul

rem Keep this script in the installer folder next to the BLACKSMITH folder.
for %%I in ("%~dp0..\BLACKSMITH") do set "SOURCE=%%~fI"
set "DESTINATION=%APPDATA%\Autodesk\Autodesk Fusion 360\API\AddIns\BLACKSMITH"

if not exist "%SOURCE%\BLACKSMITH.manifest" (
    echo ERROR: BLACKSMITH folder was not found next to the installer folder.
    echo エラー: installer フォルダーの隣に BLACKSMITH フォルダーが見つかりません。
    echo Expected / 想定パス: "%SOURCE%"
    pause
    exit /b 1
)

echo BLACKSMITH will be copied to:
echo BLACKSMITH のコピー先:
echo "%DESTINATION%"
echo.
choice /C YN /M "Copy BLACKSMITH to the Fusion add-ins folder? / Fusion のアドインフォルダーに BLACKSMITH をコピーしますか？"
if errorlevel 2 (
    echo Installation cancelled.
    echo インストールを中止しました。
    pause
    exit /b 0
)

robocopy "%SOURCE%" "%DESTINATION%" /E /R:2 /W:1
if errorlevel 8 (
    echo.
    echo ERROR: BLACKSMITH installation failed. See the copy errors above.
    echo エラー: BLACKSMITH のインストールに失敗しました。上のコピーエラーを確認してください。
    pause
    exit /b 1
)

echo.
echo BLACKSMITH installation completed. Restart Fusion if it is running.
echo BLACKSMITH のインストールが完了しました。Fusion が起動中の場合は再起動してください。
explorer.exe "%DESTINATION%"
pause
exit /b 0
