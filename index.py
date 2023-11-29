"""
TESSDRAMA: A script for batch-processing images using Tesseract and Dramatiq.
Author: Wietse Bakker on behalf of the Regionaal Archief Zuid-Utrecht
Date: 2023-11-28
License: standard MIT License

This script is used to process image files in a given source directory. It supports JPEG, JPG, TIF, and TIFF files.

The script uses the Tesseract OCR engine to process the images. The processed images are saved in a target directory, which is determined by replacing the drive letter of the source path with a target drive letter.

The script sends the image processing tasks to Dramatiq workers in batches of 100. After sending a batch, it checks the CPU usage of the system. If at least 2 cores are not fully loaded (i.e., their usage is less than 50%), it sends the next batch. Otherwise, it waits until the CPU usage drops before sending the next batch.
WARNING: This script assumes that the system has at least 2 cores. If this is not the case, the script will wait indefinitely.
WARNING: Dramatiq workers are not started by this script. This script only sends tasks to the workers. The workers must be started separately. You do this by running the following command in the command prompt: dramatiq index


For Dramatiq a REDIS-server is required. You can download an official REDIS-distribution for your operating system. No further configuration is required, Dramatiq assumes the default port. Windows users: the REDIS-server should be run with elevated rights.

The script also measures and prints the total time spent processing the images and the time spent waiting for the CPU usage to drop.

The following variables are loaded from a .env file using the python-dotenv library:
- TESSERACT_PATH: The path to the Tesseract executable.
- TESSERACT_OUTPUT: The output format of Tesseract. This should be either hocr or txt.
- TESSERACT_LANG: The language used by Tesseract. This should be a 3-letter ISO 639-2 code.
- TARGET_DRIVE_LETTER: The drive letter of the target drive. This should be a single letter without a colon.

Functions:
- index_files(source_path): Returns a list of all image files in the source path. If a JPEG or JPG file has a corresponding TIFF file in the same directory, it is assumed that the TIFF-file is of better quality and thus the JPEG is not included in the list.
- check_cpu_usage(): Returns True if at least 2 cores have a CPU usage of less than 50%, False otherwise.
- process_image(source_path, target_drive_letter): Processes an image file using Tesseract and saves the result in the target directory. This function is decorated with dramatiq.actor, which allows it to be run asynchronously by Dramatiq workers.
"""
import os
import tkinter as tk
from tkinter import filedialog
import dramatiq
import subprocess
import os
import subprocess
import os
import time
import psutil
from dotenv import load_dotenv

def ask_for_folders():
    root = tk.Tk()
    root.withdraw()  # Hide the main window

    print("Please select the source folder.")
    source_folder = filedialog.askdirectory()

    return source_folder


# This function is decorated with the Dramatiq actor decorator, which allows it to be run asynchronously by Dramatiq workers.
@dramatiq.actor(max_retries=3)
def process_image(source_path, target_drive_letter, tesseract_variables):
    # Define the valid file extensions
    valid_extensions = ['.jpg', '.jpeg', '.tif', '.tiff']
    # Get the file extension of the source file
    extension = os.path.splitext(source_path)[1].lower()

    # Check if the file extension is valid
    if extension not in valid_extensions:
        print("Invalid file extension. Only JPG, JPEG, TIF, and TIFF files are supported.")
        return

    # Check if the source file exists
    if not os.path.exists(source_path):
        print(f"Source file {source_path} does not exist.")
        return

    # Construct the target path by replacing the drive letter of the source path
    target_path = target_drive_letter + source_path[1:]
    # Get the Tesseract path, output format, and language from environment variables
    

    # Get the directory of the target path
    target_folder = os.path.dirname(target_path)
    # Create the target directory if it doesn't exist
    os.makedirs(target_folder, exist_ok=True)

    # Construct the Tesseract command
    command = [
        tesseract_variables['path'],
        source_path,
        target_path,
        '-l',
        tesseract_variables['lang'],
        tesseract_variables['output']
    ]

    # Run the Tesseract command
    subprocess.run(command)
    print(f"File {source_path} processed successfully!")

# This function returns a list of all valid image files in the source path.
def index_files(source_path):
    valid_extensions = ['.jpg', '.jpeg', '.tif', '.tiff']
    file_list = []

    # Walk through the source path
    for root, dirs, files in os.walk(source_path):
        for file in files:
            # Get the filename and extension of the file
            filename, extension = os.path.splitext(file)
            extension = extension.lower()
            # Check if the file extension is valid
            if extension in valid_extensions:
                # If the file is a JPEG or JPG file, check if a corresponding TIFF file exists
                if extension in ['.jpeg', '.jpg']:
                    tif_file = os.path.join(root, filename + '.tif')
                    # If a corresponding TIFF file exists, skip this file
                    if os.path.exists(tif_file):
                        continue
                # Construct the full file path, normalize it, and add it to the list
                file_path = os.path.normpath(os.path.join(root, file))
                file_list.append(file_path)

    return file_list

def check_cpu_usage(free_cores_wanted):
    # Get per-core CPU usage
    cpu_percentages = psutil.cpu_percent(percpu=True)
    # Count cores with less than 50% usage
    free_cores = sum(1 for percentage in cpu_percentages if percentage < 50)
    return free_cores >= free_cores_wanted

if __name__ == "__main__":
    # Load the .env file
    load_dotenv()
    
    # Get the target drive letter and source and source folders
    target_drive_letter = os.getenv('TARGET_DRIVE_LETTER')
    source_folder = ask_for_folders()
    
    # Get the Tesseract path, output format, and language from environment variables
    tesseract_variables = {}
    tesseract_variables['path'] = os.getenv('TESSERACT_PATH')
    tesseract_variables['output'] = os.getenv('TESSERACT_OUTPUT')
    tesseract_variables['lang'] = os.getenv('TESSERACT_LANG')
    
    # Get a list of all image files in the source folder
    file_list = index_files(source_folder)
    
    # Start performance counter
    start_time = time.perf_counter()

    # Send the files to the Dramatiq workers in batches of 100
    for i in range(0, len(file_list), 100):
        print("Sending a batch of 100 files to Dramatiq workers...")
        for file in file_list[i:i+100]:
            process_image.send(file, target_drive_letter, tesseract_variables)
        
        # Wait for a while for the tasks to start
        time.sleep(5)
        
        # Start performance counter of the waiting time
        start_time_wait = time.perf_counter()
        print("Waiting for CPU usage to drop...", end='') 

        # Check CPU usage before sending the next batch
        while not check_cpu_usage(2):
            # If not enough free cores, wait for a while before checking again
            print('.', end='', flush=True)
            time.sleep(2)
        
        # End performance counter of the waiting time
        end_time_wait = time.perf_counter()
        
        # Print the time spent waiting
        print('')
        print(f"Waited for {end_time_wait - start_time_wait} seconds. Currently @ {i} out of {len(file_list)}.")
    
    # Wait for the Dramatiq workers to finish, this is done through checking the cpu-usage. This assumes that the entire machine is working on this script. If this is not the case then it is best to comment-out this portion.    
    while not check_cpu_usage(psutil.cpu_count()*0.8):
        print("Waiting for Dramatiq workers to stop. You can stop this script at any time by pressing CTRL+C.")
    
    # End performance counter
    end_time = time.perf_counter()
    print(f"Processed {len(file_list)} files in {end_time - start_time} seconds.")
    
    # End of script


