# GitHub Repo to Executable

This application allows you to automatically clone a public GitHub repository and convert it into an executable file. It's designed to simplify the process of distributing applications by creating a single-click executable from the source code.

## Features

- Clones public GitHub repositories
- Automatically detects the type of project (Python, Node.js, Streamlit, etc.)
- Packages the project into a standalone executable
- Supports multiple project types:
  - Python projects (using PyInstaller)
  - **Streamlit applications** (creates a specialized launcher)
  - Node.js projects (using pkg or electron-packager)
- User-friendly web interface with Streamlit

## Requirements

- Python 3.6 or later
- Git installed and available on the PATH
- For Python projects: PyInstaller (automatically installed by the script)
- For Streamlit projects: Streamlit (automatically installed by the script)
- For Node.js projects: Node.js and npm installed and available on the PATH

## Installation

1. Clone or download this repository
2. Install the required Python dependencies:
   ```
   pip install -r requirements.txt
   ```

## Usage

### Streamlit Web Interface

Run the Streamlit app for a user-friendly web interface:

```
streamlit run app.py
```

This will open a web browser window with a simple interface where you can:
- Enter the GitHub repository URL
- Select the output directory for the executable (Downloads folder, Desktop, or custom location)
- Monitor the progress with a real-time log display
- See links to the generated executables when the process completes

### Example Repositories to Try

Here are some example GitHub repositories you can try:

1. Simple Python CLI tool:
   ```
   https://github.com/pallets/click
   ```

2. Python GUI application:
   ```
   https://github.com/python-simple-gui/PySimpleGUI-Calculator
   ```

3. Node.js CLI application:
   ```
   https://github.com/chalk/chalk
   ```

4. Streamlit application:
   ```
   https://github.com/streamlit/streamlit-example
   ```

5. Another Streamlit demo app:
   ```
   https://github.com/streamlit/demo-uber-nyc-pickups
   ```

## Supported Project Types

- **Python**: Projects with a `requirements.txt` file or Python files (`.py`)
- **Streamlit**: Applications that import or use Streamlit. Creates a special launcher executable that runs the Streamlit app correctly.
- **Node.js**: Projects with a `package.json` file or JavaScript files (`.js`)
  - Electron applications are detected and packaged appropriately

## How It Works

For Streamlit applications:
1. Detects that the project is a Streamlit app by checking for imports or usage patterns
2. Finds the main entry file for the Streamlit app
3. Creates a launcher script that properly invokes Streamlit at runtime
4. Packages everything together using PyInstaller with special flags to include Streamlit
5. The resulting executable will launch the Streamlit app automatically

## Limitations

- Currently, the script primarily supports Python, Streamlit, and Node.js projects
- For other project types (Java, Rust, Go, etc.), detection is implemented but packaging is not yet supported
- The script requires internet access to clone repositories and download dependencies
- Executables are created for the current platform only (Windows in this implementation)

## License

MIT License 