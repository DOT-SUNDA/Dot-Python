@echo off
:: Buka Profile 1
start "" "C:\Program Files\Google\Chrome\Application\chrome.exe" --user-data-dir="C:\Users\Administrator\Desktop\Profile1" --profile-directory="Default" --window-position=0,0 --new-window "https://idx.google.com/joko"

:: Buka Profile 2
start "" "C:\Program Files\Google\Chrome\Application\chrome.exe" --user-data-dir="C:\Users\Administrator\Desktop\Profile2" --profile-directory="Default" --window-position=0,600 --new-window "https://idx.google.com/joko"

exit
