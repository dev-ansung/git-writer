# Git Strategy: Parsing and Rewriting History

This document details the exact Git plumbing commands and Python logic that will be used to parse and rewrite the repository history.

## 1. How to Parse Git History

To safely parse the Git history, including commits with multi-line bodies or special characters, we will use ASCII control characters as delimiters. 

### The Git Command
We will use `git log` with strict formatting to output the graph in **reverse topological order** (guaranteeing parents are parsed before children):

```bash
git log --all --reverse --topo-order --pretty=format:"%x1E%H%x1F%P%x1F%T%x1F%an%x1F%ae%x1F%aI%x1F%cn%x1F%ce%x1F%cI%x1F%s%x1F%b"
```

*   `%x1E` (Record Separator): Used to delimit distinct commits.
*   `%x1F` (Unit Separator): Used to delimit fields within a commit.
*   `--all`: Fetches commits from all branches and tags.
*   `--reverse --topo-order`: Orders the output so the oldest commits (roots) appear first.

### Python Parsing Logic
```python
output = subprocess.check_output(cmd, encoding='utf-8')
commits = []

for commit_block in output.split('\x1e'):
    if not commit_block.strip():
        continue
        
    parts = commit_block.split('\x1f')
    hash_, parents, tree, an, ae, ad, cn, ce, cd, subject, body = parts
    
    commits.append({
        "hash": hash_,
        "parents": parents.split() if parents else [],
        "tree": tree,
        "author_name": an,
        # ... mapping the rest
    })
```

## 2. How to Edit Git History

We will use Git's low-level `commit-tree` command. This approach builds the new commit objects directly in the `.git/objects` database without ever checking out files into the working directory. This makes the rewrite practically instantaneous and completely decoupled from uncommitted local changes.

### Step-by-Step Algorithm

1.  **Backup:** Run `cp -R .git .git.bak_<timestamp>` so the user can easily restore the exact previous state if something goes wrong.
2.  **Initialize Mapping:** Create a dictionary `hash_map = {}` to map `old_commit_hash` to `new_commit_hash`.
3.  **Iterate:** Loop over the parsed commits in the reverse topological order (oldest first).
4.  **Resolve Parents:**
    For the current commit, check if its parents have been rewritten by looking them up in the `hash_map`.
    ```python
    new_parents = [hash_map.get(p, p) for p in original_parents]
    ```
5.  **Determine if Rewrite is Needed:**
    A commit needs to be recreated if:
    *   The user explicitly modified its metadata (author, date, message).
    *   ANY of its parents were rewritten (i.e., `new_parents != original_parents`).
    
    *If it does NOT need a rewrite*, simply log it in the map: `hash_map[original_hash] = original_hash`.
6.  **Recreate the Commit:**
    If a rewrite is required, use `git commit-tree`.
    *   **Arguments:** The original tree hash (`-t <tree>`) and the newly resolved parents (`-p <new_parent1> -p <new_parent2>`).
    *   **Environment Variables:** Override the commit metadata using:
        *   `GIT_AUTHOR_NAME`, `GIT_AUTHOR_EMAIL`, `GIT_AUTHOR_DATE`
        *   `GIT_COMMITTER_NAME`, `GIT_COMMITTER_EMAIL`, `GIT_COMMITTER_DATE`
    *   **Stdin:** Pass the updated commit message (or original, if unmodified) via standard input.
    
    ```python
    cmd = ["git", "commit-tree", tree_hash]
    for p in new_parents:
        cmd.extend(["-p", p])
        
    env = os.environ.copy()
    env["GIT_AUTHOR_NAME"] = updated_author_name
    # ... set other env vars ...
    
    new_hash = subprocess.check_output(cmd, env=env, input=message.encode()).decode().strip()
    hash_map[original_hash] = new_hash
    ```
7.  **Update References:**
    Once all commits are traversed and the new DAG is constructed, we must point the branches to the new tip commits.
    *   List all refs: `git for-each-ref --format="%(refname) %(objectname)" refs/`
    *   For each ref, if its `objectname` (hash) is in our `hash_map`, update it:
        ```bash
        git update-ref <refname> <new_hash>
        ```
