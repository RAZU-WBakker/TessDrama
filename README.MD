# TessDrama

## Introduction

Index.py is a script for batch-processing images using Tesseract and Dramatiq. It is designed to process image files in a given source directory, supporting JPEG, JPG, TIF, and TIFF files. The script uses the Tesseract OCR engine to process the images and saves the processed images in a target directory. The tasks are sent to Dramatiq workers in batches, and the script monitors system resources based on CPU usage.

## Use Cases

This script is particularly useful for large-scale image processing tasks where manual processing would be time-consuming. It can be used in various scenarios such as digitizing archives, processing scanned documents, and more.

## Requirements

**Please note: this script was written and tested on a Windows-machine. We cannot guarantee that it works on other operating systems.**

The script requires the following:

- Python 3.7 or higher
- Tesseract OCR
- Dramatiq
- Redis server
- python-dotenv library
- psutil library

The script also requires a .env file with the following variables. Please replace the values with your actual paths and preferences:
```
    TESSERACT_PATH='/path/to/tesseract'
    TESSERACT_OUTPUT='alto'
    TESSERACT_LANG='nld'
    TARGET_DRIVE_LETTER='A'
```
## Some examples of simple modifications

The script sends a command to tesseract (.exe in case of Windows). This command is build by the process_image-function (handled by the Dramatiq-workers):
```py
    command = [
        tesseract_variables['path'],
        source_path,
        target_path,
        '-l',
        tesseract_variables['lang'],
        tesseract_variables['output']
    ]
```

The tesseract_variables are loaded from the .env file in the mainscript and parsed to the process_image-function. You need to change these variables (the path to the tesseract executable, the output-type and the used language) in the .env-file. If you want to parse more arguments to Tesseract then you can simply add more lines to the command-variable. Do note that the first 5 lines are mandatory and sequenced. Do not change them. 

The source_path is queried to the user by the main script. The target_path is constructed by replacing the source_path-drive letter with the target_drive_letter. For example:
Given:
    source_path: 'c:/users/john/images/'
    target_drive_letter: 'x'
makes the target_path:
    target_path: 'x:/users/john/images/'

You can modify this behaviour by altering the following line:
```py
    target_path = target_drive_letter + source_path[1:]
```
Or you can question the user twice (once for a source-folder, once for a target-folder) by altering the main-script:
```py
    print("Source folder:")
    source_folder = ask_for_folders()
    print("Target folder:")
    target_folder = ask_for_folders()
    # other code, until:
    process_image.send(file, target_folder, tesseract_variables)
```

This would require you to alter the process_image script to use the target_folder parsed and to not alter it. You can do so by commenting out the original line and replacing it as such:
```py
    # target_path = target_drive_letter + source_path[1:]
    target_path = target_drive_letter
```


## Installation

1. Clone the repository or download the script.
2. Install the required Python libraries with pip:

    ```
        pip install dramatiq psutil python-dotenv
    ```

3. Install Tesseract OCR and the desired language packs. 
4. Install a Redis server. Dramatiq assumes default settings, so you don't need to configure it. Do note that Windows-users should run the Redis server as administrator. 
5. Create a .env file in the same directory as the script, and fill it with your paths and preferences.
### Start the script
6. Start the Redis-server
7. Start the Dramatiq-workers in Powershell from the folder that index.py is in:
```PS
    dramatiq index
```
**WARNING: Dramatiq starts a new worker for each CPU core. If you have 4 CPU cores, 4 workers will be started. This means that your entire system will be put to work by this script. If you want to limit the number of workers, you can do this by adding the --processes flag to the command. For example, if you want to limit the number of workers to 2, you can run the following command: dramatiq index --processes 2**

If you are developing upon this script you can add --watch to the dramatiq start command. This will restart the workers upon a saved change in index.py. Please note that this currently only works on Linux.

7. Run the script with Python:

    ```
        python index.py
    ```
8. This will prompt the user for a source folder. The script will then recursivly go through all folders and subfolders to index images and start sending them to the workers in batches of 100. Both index.py and the workers will post their progress to the console.
