@echo off
setlocal

:: Prompt the user for the path to the encrypted file to decrypt
set /p encrypted_file="Enter the path to the encrypted file (.tar.gz.enc): "

:: Check if the encrypted file exists
if not exist "%encrypted_file%" (
    echo The encrypted file does not exist! Please check the path.
    pause
    exit /b
)

:: Prompt the user to enter the password for decryption
set /p password="Enter the password for decryption: "

:: Define the output folder name for the decrypted content
set output_folder=decrypted_folder

:: Check if the output folder exists, create it if it doesn't
if not exist "%output_folder%" (
    echo Output folder does not exist. Creating folder "%output_folder%"...
    mkdir "%output_folder%"
)

:: Decrypt and extract the archive using PBKDF2
echo Decrypting and extracting %encrypted_file%...
openssl enc -d -aes-256-cbc -pbkdf2 -iter 10000 -in "%encrypted_file%" -out "%output_folder%.tar.gz" -pass pass:%password%

:: Extract the .tar.gz file
tar -xzf "%output_folder%.tar.gz" -C "%output_folder%"

:: Remove the decrypted .tar.gz file after extraction
del "%output_folder%.tar.gz"

echo The folder has been successfully decrypted and extracted into the folder: %output_folder%
pause
endlocal
