import streamlit as st
import os
import sys
import subprocess
from urllib.parse import urlparse
import shutil
import stat
import tempfile
from PIL import Image
import base64
import platform

# Set page configuration
st.set_page_config(
    page_title="Pack-n-Play",
    page_icon="🚀",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# Custom CSS for styling
st.markdown("""
<style>
    .main-title {
        text-align: center;
        font-weight: 600;
        color: #0066cc;
        margin-bottom: 20px;
    }
    .description {
        text-align: center;
        margin-bottom: 30px;
    }
    .success-message {
        padding: 20px;
        border-radius: 5px;
        background-color: #d4edda;
        color: #155724;
        text-align: center;
    }
    .stButton > button {
        width: 100%;
        background-color: #0066cc;
        color: white;
        border: none;
        padding: 12px 24px;
        border-radius: 4px;
        cursor: pointer;
        transition: all 0.3s;
    }
    .stButton > button:hover {
        background-color: #004c99;
    }
    .step-container {
        background-color: #f8f9fa;
        padding: 20px;
        border-radius: 10px;
        margin-bottom: 20px;
        border-left: 5px solid #0066cc;
    }
    .download-section {
        text-align: center;
        padding: 30px;
        border-radius: 10px;
        background-color: #f0f7ff;
        margin-top: 30px;
    }
    .footer {
        text-align: center;
        margin-top: 50px;
        padding-top: 20px;
        border-top: 1px solid #eee;
        font-size: 0.85em;
        color: #6c757d;
    }
    .section-header {
        font-weight: 600;
        margin-bottom: 15px;
        color: #333;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state variables if not already present.
if "build_complete" not in st.session_state:
    st.session_state.build_complete = False
if "clone_dir" not in st.session_state:
    st.session_state.clone_dir = ""
if "exe_name" not in st.session_state:
    st.session_state.exe_name = ""
if "exe_data" not in st.session_state:
    st.session_state.exe_data = None

def extract_repo_name(repo_url):
    """Extracts the repository name from the GitHub URL."""
    path = urlparse(repo_url).path  # e.g., '/username/repo.git'
    repo_name = os.path.basename(path)
    if repo_name.endswith('.git'):
        repo_name = repo_name[:-4]
    return repo_name

def clone_repo(repo_url, dest_dir):
    """Clones the repository from the given GitHub URL into the destination directory."""
    try:
        subprocess.check_call(['git', 'clone', repo_url, dest_dir])
    except subprocess.CalledProcessError as e:
        raise Exception(f"Error cloning repository: {e}")

def find_streamlit_script(repo_dir):
    """Searches for a potential main Streamlit script in the repository."""
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
                    st.write(f"Could not read {filepath}: {e}")
    return None

def create_wrapper_file(app_script, wrapper_filename="run_streamlit_wrapper.py"):
    """Creates a wrapper file that launches the Streamlit app."""
    app_basename = os.path.basename(app_script)
    wrapper_code = f"""\
import os
import sys
import subprocess

# If running from a PyInstaller bundle, sys._MEIPASS contains the extracted folder.
if getattr(sys, '_MEIPASS', None):
    base_path = sys._MEIPASS
    sys.path.insert(0, base_path)
else:
    base_path = os.path.abspath(".")

app_path = os.path.join(base_path, '{app_basename}')
subprocess.call(['streamlit', 'run', app_path])
"""
    with open(wrapper_filename, 'w', encoding='utf-8') as f:
        f.write(wrapper_code)
    st.write(f"Wrapper file created at {os.path.abspath(wrapper_filename)}")
    return os.path.abspath(wrapper_filename)

def build_executable(wrapper_file, exe_name_param=None, icon_file_path=None):
    """
    Uses PyInstaller to create a one-file executable from the wrapper file.
    Optionally sets the executable name and icon if provided.
    """
    try:
        # First try to import PyInstaller directly to check if it's installed in the current environment
        try:
            import PyInstaller
            st.success("✅ PyInstaller module imported successfully!")
        except ImportError:
            st.warning("⚠️ PyInstaller module could not be imported directly. Will check for executable...")
            
        # Then check if PyInstaller executable is available in path
        try:
            pyinstaller_check = subprocess.run(['pyinstaller', '--version'], 
                                             check=True, 
                                             stdout=subprocess.PIPE, 
                                             stderr=subprocess.PIPE,
                                             text=True)
            st.success(f"✅ PyInstaller executable found (version: {pyinstaller_check.stdout.strip()})")
        except (subprocess.SubprocessError, FileNotFoundError) as e:
            # Try alternative installation methods or paths
            st.error(f"⚠️ PyInstaller not found in PATH: {e}")
            
            # Try pip-installing PyInstaller if it's not already installed
            st.info("🔄 Attempting to install PyInstaller via pip...")
            try:
                subprocess.run([sys.executable, '-m', 'pip', 'install', 'pyinstaller'], 
                              check=True, 
                              stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE)
                st.success("✅ PyInstaller installed successfully via pip!")
            except subprocess.SubprocessError as pip_error:
                raise Exception(
                    f"PyInstaller is not installed or not accessible. "
                    f"Please install it manually with 'pip install pyinstaller' before running this app. "
                    f"Error details: {pip_error}"
                )

        # Use OS-specific path separator for --add-data
        separator = ';' if os.name == 'nt' else ':'
        command = [
            sys.executable, '-m', 'PyInstaller',  # Use the current Python interpreter
            '--onefile',
            '--hidden-import=streamlit.web.cli',
            '--hidden-import=streamlit.runtime.scriptrunner',
            f'--add-data=.{separator}.',
        ]
        if exe_name_param:
            command.extend(['--name', exe_name_param])
        if icon_file_path:
            # Create a PyInstaller spec file to handle paths with special characters
            spec_filename = "custom_build.spec"
            icon_path_escaped = icon_file_path.replace('\\', '\\\\')
            wrapper_path_escaped = wrapper_file.replace('\\', '\\\\')
            
            with open(spec_filename, 'w', encoding='utf-8') as spec_file:
                spec_file.write(f'''# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    [r'{wrapper_path_escaped}'],
    pathex=[],
    binaries=[],
    datas=[('.', '.')],
    hiddenimports=['streamlit.web.cli', 'streamlit.runtime.scriptrunner'],
    hookspath=[],
    hooksconfig={{}},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='{exe_name_param or os.path.splitext(os.path.basename(wrapper_file))[0]}',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=r"{icon_path_escaped}",
)
''')
            
            # Use the spec file instead of command line arguments
            command = ['pyinstaller', spec_filename]
            st.info(f"Created custom spec file to handle special characters in paths")
        else:
            command.append(wrapper_file)
        
        # Log the command for debugging
        st.info(f"Running command: {' '.join(command)}")
        
        # Run the command and capture output
        process = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False
        )
        
        if process.returncode != 0:
            error_details = process.stderr or process.stdout or "No error details available"
            raise Exception(f"PyInstaller failed (exit code {process.returncode}). Details: {error_details}")
            
    except Exception as e:
        raise Exception(f"Error during build: {str(e)}")

def cleanup_repo(clone_dir):
    """
    Deletes the cloned repository to free up space.
    Changes working directory to the repository's parent to avoid locking issues,
    and uses an onerror callback to adjust permissions.
    """
    original_dir = os.getcwd()
    os.chdir(os.path.dirname(clone_dir))
    
    def on_rm_error(func, path, exc_info):
        try:
            os.chmod(path, stat.S_IWRITE)
            func(path)
        except Exception as e:
            st.warning(f"Could not remove {path}: {str(e)}")
    
    if os.path.exists(clone_dir):
        st.info(f"Cleaning up repository at {clone_dir}...")
        try:
            shutil.rmtree(clone_dir, onerror=on_rm_error)
            st.success(f"Cleaned up repository at {clone_dir}")
        except Exception as e:
            st.warning(f"Some files could not be deleted: {str(e)}")
            st.info("Temporary files may need manual deletion.")
    else:
        st.write("Repository already cleaned up.")
    os.chdir(original_dir)



def main():
    # Header section with logo and title
    col1, col2, col3 = st.columns([1, 3, 1])
    with col2:
        st.markdown('<div class="main-title"><h1>📦 Pack-n-Play</h1></div>', unsafe_allow_html=True)
        st.markdown('<div class="description">Transform your python or streamlit app into a standalone executable with just a few clicks.</div>', unsafe_allow_html=True)
    
    
    # Create tabs for different sections
    tab1, tab2, tab3 = st.tabs(["Package App", "Documentation", "About"])
    
    with tab1:
        st.markdown("""
            <div style="padding: 1rem; border-radius: 0.5rem; background-color: #f8f9fa; border-left: 0.25rem solid #0dcaf0; color: #212529;">
            ℹ️ <b>Important Note</b>: The executable building functionality only works when running this app locally on your computer.
            This is due to security restrictions on cloud platforms that prevent running PyInstaller.<br><br>
            You can download the app here: <a href="https://public-test543464.s3.us-east-2.amazonaws.com/PacknPlay.exe">PacknPlay.exe</a>
            </div>
            """, unsafe_allow_html=True)
        # Input section
        st.markdown('<div class="section-header">📋 Project Details</div>', unsafe_allow_html=True)
        with st.container():
            st.markdown('<div class="step-container">', unsafe_allow_html=True)
            repo_url = st.text_input("GitHub Repository URL:", 
                                    placeholder="https://github.com/username/repository",
                                    help="Enter the full URL of the GitHub repository containing your Streamlit app")
            
            desired_exe_name = st.text_input("Executable Name:", 
                                            placeholder="my_streamlit_app",
                                            help="Name of the executable file to be created (without .exe extension)")
            
            icon_col1, icon_col2 = st.columns([3, 1])
            with icon_col1:
                icon_img = st.file_uploader("Icon Image:", 
                                            type=["png", "ico", "jpg", "jpeg"],
                                            help="Upload an image to use as the executable icon")
            with icon_col2:
                if icon_img:
                    image = Image.open(icon_img)
                    st.image(image, width=64, caption="Icon Preview")
            st.markdown('</div>', unsafe_allow_html=True)
                    
        # Build button
        st.markdown('<br>', unsafe_allow_html=True)
        build_col1, build_col2, build_col3 = st.columns([1, 2, 1])
        with build_col2:
            build_button = st.button("🚀 Build Executable")
        
        
        # Build process section
        if build_button:
            if not repo_url:
                st.error("⚠️ No URL provided. Please enter a repository URL.")
                return

            with st.expander("Build Process Details", expanded=True):
                try:
                    with st.spinner("🔄 Cloning repository and building executable..."):
                        # Progress bar to visualize the build process
                        progress_bar = st.progress(0)
                        
                        repo_name = extract_repo_name(repo_url)
                        clone_dir = os.path.join(os.getcwd(), repo_name)

                        if os.path.exists(clone_dir):
                            st.info(f"📂 Directory '{clone_dir}' already exists. Removing it before cloning...")
                            cleanup_repo(clone_dir)
                        
                        st.info(f"📂 Cloning repository '{repo_name}' from {repo_url} into '{clone_dir}'...")
                        clone_repo(repo_url, clone_dir)
                        progress_bar.progress(25)
                        st.success("✅ Repository cloned successfully.")

                        st.info("🔍 Searching for the main Streamlit script...")
                        streamlit_script = find_streamlit_script(clone_dir)
                        if not streamlit_script:
                            st.error("❌ Could not locate a Streamlit script in the repository.")
                            return
                        st.success(f"✅ Found Streamlit script: {streamlit_script}")
                        progress_bar.progress(50)

                        # Change to the cloned repository directory for PyInstaller.
                        os.chdir(clone_dir)
                        wrapper_file = create_wrapper_file(streamlit_script)
                        
                        # Determine executable name: use desired_exe_name if provided; otherwise default.
                        if desired_exe_name:
                            exe_name_final = desired_exe_name if desired_exe_name.lower().endswith(".exe") else desired_exe_name + ".exe"
                        else:
                            exe_name_final = os.path.splitext(os.path.basename(wrapper_file))[0] + ".exe"
                        
                        # Convert uploaded icon to ICO using PIL if provided.
                        icon_file_path = None
                        if icon_img is not None:
                            try:
                                icon_image = Image.open(icon_img)
                                safe_icon_path = os.path.join(clone_dir, "icon_safe.ico")
                                # Save as ICO with a standard size; you can adjust the size tuple as needed.
                                icon_image.save(safe_icon_path, format="ICO", sizes=[(64, 64)])
                                st.success(f"✅ Icon image converted to ICO")
                                icon_file_path = safe_icon_path
                                progress_bar.progress(60)
                            except Exception as e:
                                st.error(f"❌ Error converting icon image: {e}")
                                return

                        st.info("⚙️ Building executable using PyInstaller (this may take a few minutes)...")
                        build_executable(os.path.relpath(wrapper_file, clone_dir), exe_name_final, icon_file_path)
                        progress_bar.progress(90)
                        
                        # Determine the expected executable path.
                        executable_path = os.path.join(clone_dir, "dist", exe_name_final)
                        
                        if os.path.exists(executable_path):
                            with open(executable_path, "rb") as exe_file:
                                st.session_state.exe_data = exe_file.read()
                            progress_bar.progress(100)
                            st.success("✅ Executable created successfully!")
                        else:
                            st.error("❌ Executable file not found.")
                            return

                        # Save build details to session state.
                        st.session_state.build_complete = True
                        st.session_state.clone_dir = clone_dir
                        st.session_state.exe_name = exe_name_final

                except Exception as e:
                    st.error(f"❌ An error occurred: {str(e)}")

        # Download section
        if st.session_state.build_complete:
            st.markdown('<div class="download-section">', unsafe_allow_html=True)
            st.success(f"✅ Your executable '{st.session_state.exe_name}' is ready for download!")
            
            download_col1, download_col2, download_col3 = st.columns([1, 2, 1])
            with download_col2:
                st.download_button(
                    label="⬇️ Download Executable",
                    data=st.session_state.exe_data,
                    file_name=st.session_state.exe_name,
                    mime="application/octet-stream",
                    key="download_widget"
                )
            
            st.markdown("<br>", unsafe_allow_html=True)
            st.write("After downloading, you can clean up the temporary files:")
            cleanup_col1, cleanup_col2, cleanup_col3 = st.columns([1, 2, 1])
            with cleanup_col2:
                if st.button("🧹 Cleanup Repository", key="cleanup_button"):
                    try:
                        cleanup_repo(st.session_state.clone_dir)
                        # Clear session state variables.
                        st.session_state.build_complete = False
                        st.session_state.clone_dir = ""
                        st.session_state.exe_name = ""
                        st.session_state.exe_data = None
                        st.success("✅ Cleanup completed. Refreshing the page...")
                        st.rerun()
                    except FileNotFoundError:
                        st.error("❌ The repository directory does not exist.")
            st.markdown('</div>', unsafe_allow_html=True)
            
    with tab2:
        st.markdown("## How to Use")
        
        # Add local vs. cloud explanation
        st.markdown("""
        <div style="padding: 1rem; border-radius: 0.5rem; background-color: #f8f9fa; border-left: 0.25rem solid #0dcaf0; color: #212529;">
        ℹ️ <b>Important Note</b>: The executable building functionality only works when running this app locally on your computer.
        This is due to security restrictions on cloud platforms that prevent running PyInstaller.<br><br>
        You can download the app here: <a href="https://public-test543464.s3.us-east-2.amazonaws.com/PacknPlay.exe">PacknPlay.exe</a>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("### Local Setup")
        st.markdown("""
        To run this app locally:
        1. Clone the repository: `git clone https://github.com/yourusername/packnplay`
        2. Navigate to the directory: `cd packnplay`
        3. Install dependencies: `pip install -r requirements.txt`
        4. Run the app: `streamlit run app.py`
        """)
        
        st.markdown("### Using the App")
        st.markdown("""
        1. **Enter Repository URL**: Provide the GitHub URL of your Streamlit application
        2. **Name Your Executable**: Choose a name for your standalone application
        3. **Add an Icon** (optional): Upload an image to use as your app's icon
        4. **Build the Executable**: Click the build button and wait for the process to complete
        5. **Download**: Once built, download your executable file
        6. **Clean Up**: Remove temporary files when you're done
        
        ### Requirements
        - The repository must contain a valid Streamlit application
        - Common Streamlit app filenames like `app.py`, `streamlit_app.py`, or any Python file that imports Streamlit will be detected automatically
        - The executable will run on the same OS type it was built on (Windows executables for Windows, etc.)
        - PyInstaller must be installed on your system
        """)
        
    with tab3:
        st.markdown("## About PacknPlay")
        st.markdown("""
        This tool allows you to convert any Streamlit application into a standalone executable file that can be run without requiring Python or dependencies to be installed.
        
        **Features:**
        - Automatically identifies Streamlit scripts in repositories
        - Custom executable naming
        - Custom icon support
        - One-click build process
        - Clean and intuitive interface
        
        **Built with:**
        - Streamlit
        - PyInstaller
        - Python
        """)
    
    # Footer
    st.markdown('<div class="footer">© 2023 PacknPlay | Made with ❤️ using Streamlit</div>', unsafe_allow_html=True)

if __name__ == '__main__':
    main()
