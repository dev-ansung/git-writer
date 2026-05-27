import argparse
import os
import sys
import threading
import time
import webbrowser
from datetime import datetime
import uvicorn

from .server import app
from .git_service import get_commits, backup_git_dir, rewrite_history

def main():
    parser = argparse.ArgumentParser(description="Git History Writer")
    parser.add_argument("path", nargs="?", default=".", help="Path to the target Git repository")
    parser.add_argument("--cli", action="store_true", help="Run in command-line editor mode instead of web server")
    args = parser.parse_args()

    target_path = os.path.abspath(args.path)
    if not os.path.isdir(os.path.join(target_path, ".git")):
        print(f"Error: {target_path} is not a valid git repository (no .git folder found).")
        sys.exit(1)

    # Ensure repository is not in a detached HEAD state
    from .git_service import run_git
    try:
        run_git(["symbolic-ref", "-q", "HEAD"], cwd=target_path)
    except Exception:
        print("Error: Repository is in a detached HEAD state. Please checkout a branch before running git-writer.")
        sys.exit(1)

    os.environ["GIT_WRITER_REPO_PATH"] = target_path

    if args.cli:
        run_cli_mode(target_path)
    else:
        run_server_mode(target_path)

def run_cli_mode(target_path: str):
    print(f"Initializing Git History Writer CLI for repository: {target_path}")
    
    try:
        commits = get_commits(target_path)
    except Exception as e:
        print(f"Error reading commits: {e}")
        sys.exit(1)

    if not commits:
        print("No commits found in this repository.")
        sys.exit(0)

    history_file = os.path.join(os.getcwd(), "git-history.txt")
    
    try:
        with open(history_file, "w", encoding="utf-8") as f:
            f.write("# ==============================================================================\n")
            f.write("# GIT HISTORY WRITER - EDITABLE LOG FILE\n")
            f.write("# ==============================================================================\n")
            f.write("# Instructions:\n")
            f.write("# 1. Modify the Author, Date, and message lines below as desired.\n")
            f.write("# 2. Keep the standard format:\n")
            f.write("#      commit [hash]\n")
            f.write("#      Author: Name <email@example.com>\n")
            f.write("#      Date:   DateString\n")
            f.write("# 3. The commit message lines must be indented by 4 spaces.\n")
            f.write("# 4. Lines starting with '#' (outside of commit messages) are ignored.\n")
            f.write("# 5. Save the file and press Enter in the terminal to execute history rewrite.\n")
            f.write("# ==============================================================================\n\n")
            
            commit_blocks = []
            for commit in reversed(commits):
                block_lines = []
                block_lines.append(f"commit {commit.hash}")
                block_lines.append(f"Author: {commit.author_name} <{commit.author_email}>")
                
                try:
                    dt = datetime.fromisoformat(commit.author_date)
                    formatted_date = dt.strftime("%a %b %d %H:%M:%S %Y %z")
                except Exception:
                    formatted_date = commit.author_date
                    
                block_lines.append(f"Date:   {formatted_date}")
                block_lines.append("") # Empty line before message
                
                block_lines.append(f"    {commit.subject}")
                if commit.body and commit.body.strip():
                    for line in commit.body.strip().splitlines():
                        if line.strip():
                            block_lines.append(f"    {line}")
                        else:
                            block_lines.append("")
                commit_blocks.append("\n".join(block_lines))
                
            f.write("\n\n".join(commit_blocks))
            f.write("\n")
    except Exception as e:
        print(f"Error creating editable history file: {e}")
        sys.exit(1)

    print(f"\nCreated editable history log: {history_file}")
    print("Please open this file in your preferred text editor, make the desired changes, and save the file.")
    
    try:
        input("\nPress [Enter] to apply your changes, or Ctrl+C to abort...")
    except KeyboardInterrupt:
        print("\n\nOperation aborted by user.")
        if os.path.exists(history_file):
            os.remove(history_file)
        sys.exit(0)

    if not os.path.exists(history_file):
        print(f"Error: {history_file} was deleted or moved. Aborting.")
        sys.exit(1)

    print("\nParsing modifications...")
    try:
        with open(history_file, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except Exception as e:
        print(f"Error reading history file: {e}")
        sys.exit(1)

    edits = []
    current_commit = None
    current_fields = {}
    message_lines = []
    in_message = False

    for line in lines:
        if line.startswith("#") and not in_message:
            continue

        # Check for commit header boundary
        if line.startswith("commit ") and not in_message:
            if current_commit:
                current_fields["message"] = "".join(message_lines).strip()
                edits.append((current_commit, current_fields))

            current_commit = line.split("commit ", 1)[1].strip()
            current_fields = {}
            message_lines = []
            in_message = False
            continue

        if current_commit:
            if not in_message:
                if line.startswith("Author:"):
                    author_part = line.split("Author:", 1)[1].strip()
                    if "<" in author_part and author_part.endswith(">"):
                        name, email = author_part.rsplit("<", 1)
                        current_fields["author_name"] = name.strip()
                        current_fields["author_email"] = email.rstrip(">").strip()
                    else:
                        current_fields["author_name"] = author_part
                        current_fields["author_email"] = ""
                elif line.startswith("Date:"):
                    current_fields["author_date"] = line.split("Date:", 1)[1].strip()
                elif line == "\n" or not line.strip():
                    in_message = True
            else:
                # Check if we hit the next commit line (when in_message is True)
                if line.startswith("commit "):
                    current_fields["message"] = "".join(message_lines).strip()
                    edits.append((current_commit, current_fields))
                    
                    current_commit = line.split("commit ", 1)[1].strip()
                    current_fields = {}
                    message_lines = []
                    in_message = False
                    continue

                if line.startswith("    "):
                    message_lines.append(line[4:])
                elif line == "\n" or not line.strip():
                    message_lines.append("\n")
                else:
                    message_lines.append(line)

    if current_commit:
        current_fields["message"] = "".join(message_lines).strip()
        edits.append((current_commit, current_fields))

    original_commits_map = {c.hash: c for c in commits}
    commit_edits = []

    for hash_, fields in edits:
        orig = original_commits_map.get(hash_)
        if not orig:
            continue

        orig_message = orig.subject
        if orig.body:
            orig_message += "\n" + orig.body
        orig_message = orig_message.strip()

        try:
            orig_dt = datetime.fromisoformat(orig.author_date)
            orig_formatted_date = orig_dt.strftime("%a %b %d %H:%M:%S %Y %z")
        except Exception:
            orig_formatted_date = orig.author_date

        changed = (
            fields.get("author_name") != orig.author_name or
            fields.get("author_email") != orig.author_email or
            fields.get("author_date") != orig_formatted_date or
            fields.get("message") != orig_message
        )

        if changed:
            from .models import CommitEdit
            commit_edits.append(CommitEdit(
                hash=hash_,
                author_name=fields.get("author_name"),
                author_email=fields.get("author_email"),
                author_date=fields.get("author_date"),
                message=fields.get("message")
            ))

    if not commit_edits:
        print("No changes detected. Git history remains unchanged.")
        if os.path.exists(history_file):
            os.remove(history_file)
        sys.exit(0)

    print(f"\nDetected modifications on {len(commit_edits)} commit{'s' if len(commit_edits) != 1 else ''}.")
    print("Creating safety repository backup...")
    try:
        backup_path = backup_git_dir(target_path)
        print(f"Safety backup archived successfully at: {backup_path}")
    except Exception as e:
        print(f"Error creating safety backup: {e}. Aborting history rewrite for safety.")
        sys.exit(1)

    print("Executing atomic Git history rewrite...")
    try:
        hash_map = rewrite_history(target_path, commit_edits)
        rewritten_count = sum(1 for orig, new in hash_map.items() if orig != new)
        print(f"Successfully rewrote {rewritten_count} commit{'s' if rewritten_count != 1 else ''}!")
    except Exception as e:
        print(f"Error rewriting history: {e}")
        print("You can restore your original state from the safety backup path listed above.")
        sys.exit(1)
    finally:
        if os.path.exists(history_file):
            os.remove(history_file)

def run_server_mode(target_path: str):
    print(f"Starting Git Writer server for repository: {target_path}")
    
    def open_browser():
        time.sleep(1.5)
        webbrowser.open("http://127.0.0.1:8000")
        
    threading.Thread(target=open_browser, daemon=True).start()
    uvicorn.run(app, host="127.0.0.1", port=8000)

if __name__ == "__main__":
    main()
