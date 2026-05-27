import os
import shutil
import tempfile
import subprocess
from git_writer.git_service import get_commits, rewrite_history
from git_writer.models import CommitEdit

source_repo = "/Users/an/Development/aiq"

with tempfile.TemporaryDirectory() as temp_dir:
    test_repo = os.path.join(temp_dir, "aiq_test")
    # Clone the repo locally to not mess with the original
    subprocess.run(["git", "clone", source_repo, test_repo], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    commits = get_commits(test_repo)
    last_commit = commits[-1]
    
    print(f"Original last commit message: {last_commit.subject}")
    print(f"Original last commit author: {last_commit.author_name}")
    
    # We want to change the author and the message of the very last commit
    edits = [
        CommitEdit(
            hash=last_commit.hash,
            author_name="Super Git Writer",
            message="feat: REWRITTEN BY GIT WRITER\n\nThis is a test body."
        )
    ]
    
    print("\nExecuting rewrite...")
    hash_map = rewrite_history(test_repo, edits)
    print(f"Rewrite completed. {len(hash_map)} commits processed.")
    
    # Verify the rewrite
    new_commits = get_commits(test_repo)
    new_last_commit = new_commits[-1]
    
    print(f"\nNew last commit message: {new_last_commit.subject}")
    print(f"New last commit author: {new_last_commit.author_name}")
    print(f"New last commit hash: {new_last_commit.hash} (Old: {last_commit.hash})")
    
    # Assertions
    assert new_last_commit.author_name == "Super Git Writer"
    assert new_last_commit.subject == "feat: REWRITTEN BY GIT WRITER"
    assert new_last_commit.body == "This is a test body."
    print("\nSUCCESS! The prototype successfully rewrote the history of the AIQ repo.")
