import uvicorn
import webbrowser
import threading
import time
import sys
import os

from .server import app

def main():
    # Allow passing target repo path as positional argument
    target_path = os.getcwd()
    if len(sys.argv) > 1:
        target_path = os.path.abspath(sys.argv[1])
        
    if not os.path.isdir(os.path.join(target_path, ".git")):
        print(f"Error: {target_path} is not a valid git repository (no .git folder found).")
        sys.exit(1)
        
    os.environ["GIT_WRITER_REPO_PATH"] = target_path
    print(f"Starting Git Writer server for repository: {target_path}")
    
    # Open browser after a short delay
    def open_browser():
        time.sleep(1.5)
        webbrowser.open("http://127.0.0.1:8000")
        
    threading.Thread(target=open_browser, daemon=True).start()
    
    # Start the Uvicorn server
    uvicorn.run(app, host="127.0.0.1", port=8000)

if __name__ == "__main__":
    main()
