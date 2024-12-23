@echo off
setlocal

:: Prompt the user for the path to the folder to encrypt
set /p folder_path="Enter the path of the folder to encrypt: "

:: Check if the folder exists
if not exist "%folder_path%" (
    echo The folder does not exist! Please check the path.
    pause
    exit /b
)

:: Prompt the user to enter a password for encryption
set /p password="Enter the password for encryption: "

:: Define the output file name (encrypted .tar.gz file)
set output_file=%folder_path%.tar.gz.enc

:: Encrypt the folder: compress it and encrypt the archive using PBKDF2 with 10000 iterations
echo Compressing and encrypting the folder %folder_path%...
tar -czf - "%folder_path%" | openssl enc -aes-256-cbc -salt -pbkdf2 -iter 10000 -out "%output_file%" -pass pass:%password%

echo The folder has been successfully encrypted and saved as: %output_file%
pause
endlocal
