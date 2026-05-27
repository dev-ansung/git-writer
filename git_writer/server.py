import os
from typing import List
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .models import CommitResponse, RewriteRequest, RewriteResponse
from .git_service import get_commits, rewrite_history, backup_git_dir, run_git

app = FastAPI(title="Git Writer API")

# Allow CORS for local development of the frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# We expect the git repository to be specified by GIT_WRITER_REPO_PATH or fallback to current working directory
def get_repo_path() -> str:
    return os.getenv("GIT_WRITER_REPO_PATH", os.getcwd())

@app.get("/api/commits", response_model=List[CommitResponse])
def api_get_commits():
    """Get the commit history of the current repository."""
    try:
        return get_commits(get_repo_path())
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/repo")
def api_repo():
    """Get the repository metadata."""
    try:
        path = get_repo_path()
        folder_name = os.path.basename(path)
        parent_dir = os.path.basename(os.path.dirname(path))
        
        try:
            branch = run_git(["branch", "--show-current"], cwd=path).strip()
        except Exception:
            branch = "main"
            
        return {
            "path": path,
            "name": folder_name,
            "owner": parent_dir or "local",
            "branch": branch or "main"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/rewrite", response_model=RewriteResponse)
def api_rewrite(request: RewriteRequest):
    """Rewrite the git history with the requested edits."""
    repo_path = get_repo_path()
    try:
        # Step 1: Backup
        backup_path = backup_git_dir(repo_path)
        
        # Step 2: Rewrite
        hash_map = rewrite_history(repo_path, request.edits)
        
        rewritten_count = sum(1 for orig, new in hash_map.items() if orig != new)
        
        return RewriteResponse(
            success=True,
            message=f"Successfully rewrote {rewritten_count} commit{'s' if rewritten_count != 1 else ''}.",
            backup_path=backup_path,
            hash_map=hash_map
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# If the frontend has been built, serve it from the dist directory
# (This is used when the package is distributed via uvx)
FRONTEND_DIST = os.path.join(os.path.dirname(__file__), "..", "frontend", "dist")
if os.path.isdir(FRONTEND_DIST):
    app.mount("/", StaticFiles(directory=FRONTEND_DIST, html=True), name="static")
