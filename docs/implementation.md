# Git Writer - Implementation Document

## 1. Project Initialization
## 1. Project Initialization
We will set up a Python package structure with a bundled frontend.

*   `git_writer/`: The Python package containing the FastAPI backend and CLI entrypoint.
*   `frontend/`: React + Vite single-page application.
*   The project will use `pyproject.toml` and `uv` for dependency management.
*   The built frontend assets (`frontend/dist`) will be included in the Python package data so it works seamlessly via `uvx`.

## 2. Implementation Phases

### Phase 1: Backend Setup & Git Read Operations
*   Initialize `pyproject.toml` using `uv init`.
*   Create a FastAPI server and CLI entrypoint (using `argparse` or `typer` to launch the server and open the browser).
*   Implement a `GET /api/commits` endpoint.
*   Use Python's `subprocess` to run `git log --all --pretty=format:"%H|%P|%T|%an|%ae|%aI|%cn|%ce|%cI|%s|%b"`.
*   Parse the output into a structured JSON array of commit objects.
*   Handle empty repositories and common Git errors.

### Phase 2: Frontend Foundation & UI
*   Initialize the Vite React project.
*   Configure styling (Vanilla CSS with CSS variables for theming, or Tailwind if strictly needed, but sticking to pure CSS for maximum control as per guidelines).
*   Create components:
    *   `Timeline`: Renders the commit DAG chronologically.
    *   `CommitCard`: Displays individual commit details.
    *   `CommitEditor`: A form to edit Author Name, Email, Date, and Message.
*   Implement state management to hold the parsed commits and track user edits.

### Phase 3: Backend Git Write Operations (The Engine)
*   Implement a `POST /api/rewrite` endpoint that receives the modified commit data.
*   **Step 1 (Backup):** Execute `cp -R .git .git.bak_<timestamp>` to ensure user data safety.
*   **Step 2 (Rebuild Graph):**
    *   Maintain a mapping of `oldHash -> newHash`.
    *   Iterate through the commits from oldest to newest (topological sort).
    *   For each commit:
        *   Determine new parent hashes using the mapping.
        *   If the commit and its parents are unmodified, keep the old hash (wait, if parents change, the hash *must* change. If neither changed, we can skip `commit-tree` and just map `oldHash -> oldHash`).
        *   Execute `git commit-tree` with the appropriate environment variables and parent arguments.
        *   Store the resulting hash in the mapping.
*   **Step 3 (Update Refs):**
    *   Determine which branches point to the rewritten commits.
    *   Use `git update-ref` to move branch pointers to the new tip hashes.

### Phase 4: Integration & Polish
*   Connect the frontend "Save" action to the backend endpoint.
*   Show a loading state during the rewrite process.
*   Display a success notification and reload the timeline upon completion.
*   Add error boundaries and robust error logging.

## 3. Technology Stack specifics
*   **Backend:** Python 3.10+, FastAPI, `subprocess`, `uvicorn`.
*   **Frontend:** React 18, Vite, Lucide React (for icons), native `fetch` API.
