@echo off

:: Buka Profile 1 di posisi 0,0 dengan ukuran 500x500
start "" "C:\Program Files\Google\Chrome\Application\chrome.exe" ^
  --user-data-dir="C:\Users\Administrator\Desktop\Profile1" ^
  --profile-directory="Default" ^
  --window-position=0,0 ^
  --window-size=500,500 ^
  --new-window "https://idx.google.com/joko"

timeout /t 2 >nul

:: Buka Profile 2 di posisi 0,500 (di bawahnya) dengan ukuran 500x500
start "" "C:\Program Files\Google\Chrome\Application\chrome.exe" ^
  --user-data-dir="C:\Users\Administrator\Desktop\Profile2" ^
  --profile-directory="Default" ^
  --window-position=0,0 ^
  --window-size=500,500 ^
  --new-window "https://idx.google.com/joko"

exit
