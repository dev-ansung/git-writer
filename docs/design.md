# Git Writer - Design Document

## 1. Overview
Git Writer is a local, web-based tool designed to allow users to intuitively and safely rewrite their Git repository's history. It abstracts away the complexity of interactive rebasing and provides a clean UI to modify commit dates, authors, and messages.

## 2. Architecture
The application follows a lightweight local Client-Server architecture:
*   **Backend:** A Python application (using FastAPI) managed by `uv`. It interfaces directly with the local Git repository using Git plumbing commands via `subprocess`.
*   **Frontend:** A modern Web UI (built with React/Vite) served directly by the Python backend. The frontend assets will be bundled into the Python package so the tool can be run instantly via `uvx --from git+...`.
*   **Communication:** RESTful API for fetching the commit graph and submitting the rewritten history.

## 3. Git Interaction Strategy (The Core Engine)
To ensure maximum performance and safety without touching the user's working directory, Git Writer will use Git's low-level plumbing commands instead of high-level commands like `git rebase`:

### 3.1. Reading History
*   The backend will execute a custom `git log` command to extract the entire commit DAG (Directed Acyclic Graph).
*   Format string: `%H` (hash), `%P` (parents), `%T` (tree), `%an` (author name), `%ae` (author email), `%aI` (author date), `%s` (subject), `%b` (body).

### 3.2. Rewriting History
*   **Backup:** Before any destructive operation, the `.git` directory will be duplicated (e.g., to `.git.bak_<timestamp>`).
*   **Rebuilding the DAG:**
    *   The backend will perform a topological traversal of the commits from oldest to newest.
    *   For each commit, a new commit object is created using `git commit-tree <tree-hash> -p <new-parent-hashes>`.
    *   Environment variables (`GIT_AUTHOR_NAME`, `GIT_AUTHOR_DATE`, etc.) are used to inject the modified metadata.
*   **Updating References:** Once the new commit graph is built, branch tips (e.g., `refs/heads/main`) are updated to point to the new tip commits using `git update-ref`.

## 4. User Interface & Experience
*   **Aesthetics:** Premium, modern design featuring a dark mode, smooth micro-animations, and clear typography.
*   **Layout:**
    *   **Main View:** A vertical timeline or list representing the commit history.
    *   **Edit View:** Inline editing or a side panel to modify Author, Date, and Message for a selected commit.
    *   **Action Bar:** A sticky bar with a "Save Changes" button to execute the rewrite.
*   **Safety Feedback:** Clear visual indicators showing what will be modified, and confirmation dialogs before executing the Git operations.
