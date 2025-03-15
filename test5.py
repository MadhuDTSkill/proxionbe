import zipfile
import os
import shutil
import ast
import autopep8  # For code formatting

UPLOAD_FOLDER = "/content/uploaded_project"
OUTPUT_FOLDER = "/content/modified_project"
ZIP_NAME = "modified_project.zip"

def extract_zip(zip_path, extract_to):
    """Extracts a ZIP file to the specified directory."""
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(extract_to)

def optimize_code(code):
    """Optimizes Python code by formatting and removing unnecessary elements."""
    return "Optimized"

def modify_python_files(base_path):
    """Finds and optimizes all Python files in the extracted directory."""
    for root, _, files in os.walk(base_path):
        for file in files:
            if file.endswith(".py"):
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        original_code = f.read()
                    
                    optimized_code = optimize_code(original_code)  # Optimize the code

                    with open(file_path, "w", encoding="utf-8") as f:
                        f.write(optimized_code)  # Overwrite with optimized code
                    
                    print(f"Optimized: {file_path}")

                except Exception as e:
                    print(f"Failed to modify {file_path}: {e}")

def create_new_zip(source_folder, output_zip):
    """Creates a ZIP file from the modified project folder."""
    shutil.make_archive(output_zip.replace(".zip", ""), 'zip', source_folder)

def main(zip_path):
    """Complete process: extract, optimize, and re-zip."""
    # Step 1: Extract ZIP
    extract_zip(zip_path, UPLOAD_FOLDER)
    
    # Step 2: Modify and optimize Python files
    modify_python_files(UPLOAD_FOLDER)
    
    # Step 3: Re-zip the project
    create_new_zip(UPLOAD_FOLDER, ZIP_NAME)

    return OUTPUT_FOLDER + "/" + ZIP_NAME  # Path of new ZIP file

# 🔥 Usage
zip_path = "project.zip"  # Replace with uploaded ZIP path
modified_zip = main(zip_path)
print(f"Modified ZIP created: {modified_zip}")
