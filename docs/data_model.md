# Git Writer - Data Model

This document defines the core Pydantic data models used for validation between the React frontend and the FastAPI backend.

## 1. Commit Representation (API Response)
When the frontend requests the commit graph (`GET /api/commits`), the backend parses the `git log` and returns a list of `CommitResponse` objects.

```python
from pydantic import BaseModel, Field
from typing import List, Optional

class CommitResponse(BaseModel):
    hash: str = Field(..., description="The original SHA-1 hash of the commit")
    parents: List[str] = Field(..., description="List of parent SHA-1 hashes")
    tree: str = Field(..., description="The SHA-1 hash of the commit's tree")
    
    # Author details
    author_name: str
    author_email: str
    author_date: str = Field(..., description="Author date in ISO 8601 format")
    
    # Committer details
    committer_name: str
    committer_email: str
    committer_date: str = Field(..., description="Committer date in ISO 8601 format")
    
    # Message
    subject: str = Field(..., description="First line of the commit message")
    body: str = Field(..., description="The remainder of the commit message")
```

## 2. Rewrite Request (API Request)
When the user clicks "Save", the frontend submits a `POST /api/rewrite` request containing only the commits that have been modified.

```python
class CommitEdit(BaseModel):
    hash: str = Field(..., description="The original SHA-1 hash of the commit being edited")
    
    # Optional fields: if provided, the backend will overwrite the original commit's data
    author_name: Optional[str] = None
    author_email: Optional[str] = None
    author_date: Optional[str] = Field(None, description="New author date in ISO 8601 format")
    
    committer_name: Optional[str] = None
    committer_email: Optional[str] = None
    committer_date: Optional[str] = Field(None, description="New committer date in ISO 8601 format")
    
    message: Optional[str] = Field(None, description="The complete new commit message (subject and body combined)")

class RewriteRequest(BaseModel):
    edits: List[CommitEdit] = Field(
        ..., 
        description="A list of edits. Only commits that have been modified need to be included."
    )
```

## 3. Rewrite Response
The backend responds with the status of the operation and a mapping of the rewritten hashes.

```python
class RewriteResponse(BaseModel):
    success: bool
    message: str = Field(..., description="Success or error message")
    backup_path: Optional[str] = Field(None, description="The path to the `.git` backup directory created")
    hash_mapping: dict[str, str] = Field(
        default_factory=dict, 
        description="Mapping from the old commit hash to the newly generated commit hash"
    )
```
