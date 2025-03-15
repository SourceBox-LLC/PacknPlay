import os
import sys
import subprocess

if getattr(sys, '_MEIPASS', None):
    base_path = sys._MEIPASS
    sys.path.insert(0, base_path)
else:
    base_path = os.path.abspath(".")

subprocess.call(['streamlit', 'run', os.path.join(base_path, 'app.py')])