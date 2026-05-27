import os
import shutil
import subprocess
from datetime import datetime
from typing import List, Dict

from .models import CommitResponse, CommitEdit

def run_git(args: List[str], cwd: str, env: Dict[str, str] = None, input_data: bytes = None) -> str:
    """Run a git command and return its stdout as a string."""
    try:
        result = subprocess.run(
            ["git"] + args,
            cwd=cwd,
            env=env,
            input=input_data,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True
        )
        return result.stdout.decode('utf-8')
    except subprocess.CalledProcessError as e:
        error_msg = e.stderr.decode('utf-8')
        raise RuntimeError(f"Git command failed: git {' '.join(args)}\nError: {error_msg}")

def get_commits(repo_path: str) -> List[CommitResponse]:
    """Parse the git log and return a list of commits."""
    # Ensure it's a git repo
    if not os.path.isdir(os.path.join(repo_path, ".git")):
        raise ValueError(f"Not a git repository: {repo_path}")

    # Format: %x1E (Record Separator) %x1F (Unit Separator)
    # Fields: hash, parents, tree, author_name, author_email, author_date,
    #         committer_name, committer_email, committer_date, subject, body
    git_log_format = "%x1E%H%x1F%P%x1F%T%x1F%an%x1F%ae%x1F%aI%x1F%cn%x1F%ce%x1F%cI%x1F%s%x1F%b"
    args = ["log", "--all", "--reverse", "--topo-order", f"--pretty=format:{git_log_format}"]
    
    try:
        output = run_git(args, cwd=repo_path)
    except RuntimeError:
        # Repository might have no commits yet
        return []

    commits = []
    for commit_block in output.split('\x1e'):
        if not commit_block.strip():
            continue
            
        parts = commit_block.split('\x1f')
        if len(parts) < 11:
            continue
            
        hash_, parents, tree, an, ae, ad, cn, ce, cd, subject, body = parts
        
        commits.append(CommitResponse(
            hash=hash_,
            parents=parents.split() if parents else [],
            tree=tree,
            author_name=an,
            author_email=ae,
            author_date=ad,
            committer_name=cn,
            committer_email=ce,
            committer_date=cd,
            subject=subject,
            body=body
        ))
    
    # We parsed in reverse topological order, which is correct for processing,
    # but the UI typically wants newest first. We return it exactly as parsed.
    return commits

def backup_git_dir(repo_path: str) -> str:
    """Create a backup of the .git directory."""
    git_dir = os.path.join(repo_path, ".git")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = os.path.join(repo_path, f".git.bak_{timestamp}")
    
    shutil.copytree(git_dir, backup_dir)
    return backup_dir

def rewrite_history(repo_path: str, edits: List[CommitEdit]) -> Dict[str, str]:
    """
    Rewrite the git history applying the requested edits.
    Returns a mapping of old_hash to new_hash.
    """
    # 1. Get all commits in reverse topological order (oldest first)
    all_commits = get_commits(repo_path)
    if not all_commits:
        return {}

    # 2. Build a quick lookup for edits
    edits_map = {edit.hash: edit for edit in edits}
    
    # 3. Initialize mapping and env
    hash_map: Dict[str, str] = {}
    base_env = os.environ.copy()

    # 4. Iterate and rebuild
    for commit in all_commits:
        original_hash = commit.hash
        original_parents = commit.parents
        
        # Determine new parents
        new_parents = [hash_map.get(p, p) for p in original_parents]
        parents_changed = new_parents != original_parents
        
        edit = edits_map.get(original_hash)
        
        # If no edit and parents didn't change, we don't need to rewrite this commit
        if not edit and not parents_changed:
            hash_map[original_hash] = original_hash
            continue
            
        # We need to recreate the commit
        # Prepare metadata
        env = base_env.copy()
        
        if edit and edit.author_name is not None:
            env["GIT_AUTHOR_NAME"] = edit.author_name
        else:
            env["GIT_AUTHOR_NAME"] = commit.author_name
            
        if edit and edit.author_email is not None:
            env["GIT_AUTHOR_EMAIL"] = edit.author_email
        else:
            env["GIT_AUTHOR_EMAIL"] = commit.author_email
            
        if edit and edit.author_date is not None:
            env["GIT_AUTHOR_DATE"] = edit.author_date
        else:
            env["GIT_AUTHOR_DATE"] = commit.author_date
            
        if edit and edit.committer_name is not None:
            env["GIT_COMMITTER_NAME"] = edit.committer_name
        else:
            env["GIT_COMMITTER_NAME"] = commit.committer_name
            
        if edit and edit.committer_email is not None:
            env["GIT_COMMITTER_EMAIL"] = edit.committer_email
        else:
            env["GIT_COMMITTER_EMAIL"] = commit.committer_email
            
        if edit and edit.committer_date is not None:
            env["GIT_COMMITTER_DATE"] = edit.committer_date
        else:
            env["GIT_COMMITTER_DATE"] = commit.committer_date
            
        # Determine final co-authors list
        if edit and edit.message is not None:
            message = edit.message
        else:
            message = f"{commit.subject}\n\n{commit.body}".strip()
            
        # Run commit-tree
        cmd = ["commit-tree", commit.tree]
        for p in new_parents:
            cmd.extend(["-p", p])
            
        new_hash = run_git(cmd, cwd=repo_path, env=env, input_data=message.encode('utf-8')).strip()
        hash_map[original_hash] = new_hash

    # 5. Update branch and tag references
    # We need to know all local refs
    refs_output = run_git(["for-each-ref", "--format=%(refname) %(objectname)"], cwd=repo_path)
    for line in refs_output.splitlines():
        if not line.strip():
            continue
        refname, objectname = line.split()
        if objectname in hash_map and hash_map[objectname] != objectname:
            run_git(["update-ref", refname, hash_map[objectname]], cwd=repo_path)

    return hash_map
