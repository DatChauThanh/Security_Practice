@echo off
setlocal

:: Prompt the user for the path to the encrypted file to decrypt
set /p encrypted_file="Enter the path to the encrypted file (.enc.2): "

:: Check if the encrypted file exists
if not exist "%encrypted_file%" (
    echo The encrypted file does not exist! Please check the path.
    pause
    exit /b
)

:: Prompt the user to enter the password for decryption
set /p password="Enter the password for decryption: "

:: Extract the base name of the encrypted file (without path and extension)
for %%f in ("%encrypted_file%") do (
    set "base_name=%%~nf"
    set "base_name=%%~nf"
)

:: Remove the .enc.2 part from the base name
set "output_folder=%base_name:.enc=%"
set "output_folder=%output_folder:.2=%"

:: Check if the output folder exists, create it if it doesn't
if not exist "%output_folder%" (
    echo Output folder does not exist. Creating folder "%output_folder%"...
    mkdir "%output_folder%"
)

:: Decrypt the first layer (des-ede3-cbc)
echo Decrypting the first layer (des-ede3-cbc)...
openssl enc -d -des-ede3-cbc -pbkdf2 -iter 11102 -in "%encrypted_file%" -out "%output_folder%.enc" -pass pass:%password%
if errorlevel 1 (
    echo Failed to decrypt the first layer. Please check the password and try again.
    timeout /t 5
    endlocal
    exit /b
)

:: Decrypt the second layer (aes-256-cbc) and extract the archive using PBKDF2
echo Decrypting the second layer (aes-256-cbc) and extracting %output_folder%.enc...
openssl enc -d -aes-256-cbc -pbkdf2 -iter 10000 -in "%output_folder%.enc" -out "%output_folder%.tar.gz" -pass pass:%password%
if errorlevel 1 (
    echo Failed to decrypt the second layer. Please check the password and try again.
    timeout /t 5
    endlocal
    exit /b
)

:: Extract the .tar.gz file
tar -xzf "%output_folder%.tar.gz" -C "%output_folder%"
if errorlevel 1 (
    echo Failed to Extract. Please check the password and try again.
    timeout /t 5
    endlocal
    exit /b
)
:: Remove the decrypted .tar.gz file after extraction
del "%output_folder%.tar.gz"
del "%output_folder%.enc"

echo The folder has been successfully decrypted and extracted into the folder: %output_folder%
timeout /t 5
endlocal