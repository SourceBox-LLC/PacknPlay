import os
import sys
import subprocess
from urllib.parse import urlparse
import shutil

def extract_repo_name(repo_url):
    """
    Extracts the repository name from the GitHub URL.
    """
    path = urlparse(repo_url).path  # e.g., '/username/repo.git'
    repo_name = os.path.basename(path)
    if repo_name.endswith('.git'):
        repo_name = repo_name[:-4]
    return repo_name

def clone_repo(repo_url, dest_dir):
    """
    Clones the repository from the given GitHub URL into the destination directory.
    """
    try:
        subprocess.check_call(['git', 'clone', repo_url, dest_dir])
    except subprocess.CalledProcessError as e:
        print(f"Error cloning repository: {e}")
        sys.exit(1)

def find_streamlit_script(repo_dir):
    """
    Searches for a potential main Streamlit script.
    Looks for common file names or any .py file that imports streamlit.
    """
    candidates = ['streamlit_app.py', 'app.py', 'main.py']
    for candidate in candidates:
        candidate_path = os.path.join(repo_dir, candidate)
        if os.path.isfile(candidate_path):
            return candidate_path

    # Fallback: search for any .py file that contains "streamlit"
    for root, _, files in os.walk(repo_dir):
        for file in files:
            if file.endswith(".py"):
                filepath = os.path.join(root, file)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = f.read()
                        if 'streamlit' in content.lower():
                            return filepath
                except Exception as e:
                    print(f"Could not read {filepath}: {e}")
    return None

def create_wrapper_file(app_script, wrapper_filename="run_streamlit_wrapper.py"):
    """
    Creates a wrapper file that launches the Streamlit app.
    When running as a one-file executable, bundled files are extracted to sys._MEIPASS.
    """
    app_basename = os.path.basename(app_script)
    wrapper_code = f"""\
import os
import sys
import subprocess

# If running from a PyInstaller bundle, sys._MEIPASS contains the extracted folder.
if getattr(sys, '_MEIPASS', None):
    base_path = sys._MEIPASS
    # Add the bundled folder to sys.path so that all modules can be imported.
    sys.path.insert(0, base_path)
else:
    base_path = os.path.abspath(".")

# Build the absolute path to the Streamlit app.
app_path = os.path.join(base_path, '{app_basename}')

# Launch the Streamlit app using its CLI.
subprocess.call(['streamlit', 'run', app_path])
"""
    with open(wrapper_filename, 'w', encoding='utf-8') as f:
        f.write(wrapper_code)
    print(f"Wrapper file created at {os.path.abspath(wrapper_filename)}")
    return os.path.abspath(wrapper_filename)

def build_executable(wrapper_file):
    """
    Uses PyInstaller to create a one-file executable from the wrapper file.
    Here we include the entire repository folder (".") as extra data so that all project files are bundled.
    """
    try:
        # On Windows, the --add-data flag uses a semicolon (;) as delimiter.
        # The argument "--add-data=.;." tells PyInstaller to bundle everything from the current folder.
        subprocess.check_call([
            'pyinstaller',
            '--onefile',
            '--hidden-import=streamlit.web.cli',
            '--hidden-import=streamlit.runtime.scriptrunner',
            '--add-data=.;.',
            wrapper_file
        ])
    except subprocess.CalledProcessError as e:
        print(f"Error during build: {e}")
        sys.exit(1)

def main():
    repo_url = input("Enter the GitHub URL of the local Streamlit app repository: ").strip()
    if not repo_url:
        print("No URL provided. Exiting.")
        sys.exit(1)

    repo_name = extract_repo_name(repo_url)
    clone_dir = os.path.join(os.getcwd(), repo_name)

    if os.path.exists(clone_dir):
        print(f"The directory '{clone_dir}' already exists. Please remove it or choose a different location.")
        sys.exit(1)

    print(f"Cloning repository '{repo_name}' from {repo_url} into '{clone_dir}'...")
    clone_repo(repo_url, clone_dir)
    print("Repository cloned successfully.")

    print("Searching for the main Streamlit script...")
    streamlit_script = find_streamlit_script(clone_dir)
    if not streamlit_script:
        print("Could not locate a Streamlit script in the repository.")
        sys.exit(1)
    print(f"Found Streamlit script: {streamlit_script}")

    # Change working directory to the repository folder so that PyInstaller includes all project files.
    os.chdir(clone_dir)

    # Create a wrapper file that will launch the Streamlit app.
    wrapper_file = create_wrapper_file(streamlit_script)

    print("Building executable using PyInstaller...")
    build_executable(os.path.relpath(wrapper_file, clone_dir))
    print("Executable created successfully.")
    print(f"You can find the executable in the 'dist' folder within '{clone_dir}'.")

    # Optional: cleanup PyInstaller build files.
    cleanup = input("Cleanup PyInstaller build files? (y/n): ").strip().lower()
    if cleanup == 'y':
        for folder in ['build', '__pycache__']:
            folder_path = os.path.join(clone_dir, folder)
            if os.path.isdir(folder_path):
                shutil.rmtree(folder_path)
        spec_file = os.path.join(clone_dir, f"{os.path.basename(wrapper_file).split('.')[0]}.spec")
        if os.path.exists(spec_file):
            os.remove(spec_file)
        print("Cleanup complete.")

if __name__ == '__main__':
    main()
