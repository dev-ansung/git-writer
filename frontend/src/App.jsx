import { useState, useEffect } from 'react'
import './App.css'

function App() {
  const [commits, setCommits] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [repoInfo, setRepoInfo] = useState({ owner: 'local', name: 'taste-skill', branch: 'main' })
  
  // Track edits by hash: { [hash]: { author_name, author_email, author_date, message } }
  const [edits, setEdits] = useState({})
  // Track which commit is currently open in the edit form
  const [editingHash, setEditingHash] = useState(null)
  // Save status states
  const [saving, setSaving] = useState(false)
  const [showConfirm, setShowConfirm] = useState(false)
  const [successResult, setSuccessResult] = useState(null)

  // Helper to format full commit message safely
  const getFullMessage = (commit) => {
    if (!commit.body) return commit.subject
    return `${commit.subject}\n\n${commit.body}`.trim()
  }

  // Fetch commits
  const fetchCommits = () => {
    setLoading(true)
    setError(null)
    fetch('/api/commits')
      .then((res) => {
        if (!res.ok) throw new Error('Failed to fetch commits')
        return res.json()
      })
      .then((data) => {
        // Keep in reverse topological order (newest at the top)
        setCommits([...data].reverse())
        setLoading(false)
      })
      .catch((err) => {
        console.error(err)
        setError(err.message)
        setLoading(false)
      })
  }

  // Fetch repo metadata
  const fetchRepoInfo = () => {
    fetch('/api/repo')
      .then((res) => {
        if (!res.ok) throw new Error('Failed to fetch repo metadata')
        return res.json()
      })
      .then((data) => {
        setRepoInfo(data)
      })
      .catch((err) => console.error('Error fetching repo info:', err))
  }

  useEffect(() => {
    fetchCommits()
    fetchRepoInfo()
  }, [])

  // Start editing a commit
  const handleStartEdit = (commit) => {
    setEditingHash(commit.hash)
    if (!edits[commit.hash]) {
      // Initialize edit fields with current commit values
      setEdits({
        ...edits,
        [commit.hash]: {
          author_name: commit.author_name,
          author_email: commit.author_email,
          author_date: commit.author_date,
          message: getFullMessage(commit),
        },
      })
    }
  }

  // Handle input changes inside the editor form
  const handleInputChange = (hash, field, value) => {
    setEdits({
      ...edits,
      [hash]: {
        ...edits[hash],
        [field]: value,
      },
    })
  }

  // Revert changes for a specific commit
  const handleRevert = (hash) => {
    const commit = commits.find((c) => c.hash === hash)
    if (!commit) return
    
    setEdits({
      ...edits,
      [hash]: {
        author_name: commit.author_name,
        author_email: commit.author_email,
        author_date: commit.author_date,
        message: getFullMessage(commit),
      },
    })
  }

  // Check if a commit is modified compared to its original state
  const isModified = (commit) => {
    const edit = edits[commit.hash]
    if (!edit) return false
    
    return (
      edit.author_name !== commit.author_name ||
      edit.author_email !== commit.author_email ||
      edit.author_date !== commit.author_date ||
      edit.message.trim() !== getFullMessage(commit)
    )
  }

  // Submit edits to backend
  const handleSave = () => {
    setSaving(true)
    setError(null)
    
    // Prepare only modified commits for payload
    const payloadEdits = Object.keys(edits)
      .filter((hash) => {
        const commit = commits.find((c) => c.hash === hash)
        return commit && isModified(commit)
      })
      .map((hash) => ({
        hash,
        author_name: edits[hash].author_name,
        author_email: edits[hash].author_email,
        author_date: edits[hash].author_date,
        message: edits[hash].message,
      }))

    fetch('/api/rewrite', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ edits: payloadEdits }),
    })
      .then((res) => {
        if (!res.ok) return res.json().then((d) => { throw new Error(d.detail || 'Save failed') })
        return res.json()
      })
      .then((data) => {
        setSaving(false)
        setShowConfirm(false)
        setSuccessResult(data)
        setEdits({}) // Clear edits
        setEditingHash(null)
      })
      .catch((err) => {
        console.error(err)
        setError(err.message)
        setSaving(false)
        setShowConfirm(false)
      })
  }

  // Group commits by author date
  const groupCommitsByDate = (commitsList) => {
    const groups = {}
    commitsList.forEach((commit) => {
      const dateStr = new Date(commit.author_date).toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'long',
        day: 'numeric',
      })
      if (!groups[dateStr]) groups[dateStr] = []
      groups[dateStr].push(commit)
    })
    return groups
  }

  // Helper to format committed time ago or locale time
  const getCommittedInfo = (commit) => {
    const date = new Date(commit.author_date)
    const now = new Date()
    const diffMs = now - date
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24))
    
    let relative = ''
    if (diffDays === 0) relative = 'today'
    else if (diffDays === 1) relative = 'yesterday'
    else if (diffDays > 1 && diffDays < 30) relative = `${diffDays} days ago`
    else relative = `on ${date.toLocaleDateString()}`
    
    return `committed ${relative}`
  }

  const modifiedCommitsCount = commits.filter(isModified).length
  const groupedCommits = groupCommitsByDate(commits)

  if (loading) {
    return (
      <div className="loading-screen">
        <div className="spinner"></div>
        <span>Parsing Git repository log...</span>
      </div>
    )
  }

  return (
    <div className="app-container">
      {/* Standalone Brand Header bar */}
      <header className="main-header">
        <div className="brand">
          <h1>
            <svg aria-hidden="true" height="16" viewBox="0 0 16 16" version="1.1" width="16" fill="currentColor">
              <path fillRule="evenodd" d="M11.75 2.5a.75.75 0 100 1.5.75.75 0 000-1.5zm-2.25.75a2.25 2.25 0 113 2.122V10.63a2.251 2.251 0 11-1.5 0V5.372A2.25 2.25 0 019.5 3.25zM11 12a.75.75 0 100 1.5.75.75 0 000-1.5zm-5.25-1.25a.75.75 0 100 1.5.75.75 0 000-1.5zM7.25 12a2.25 2.25 0 11-3-2.122V3.75a.75.75 0 011.5 0v6.878A2.25 2.25 0 017.25 12z"></path>
            </svg>
            git-writer
          </h1>
          <span className="separator">/</span>
          <span className="repo-name">{repoInfo.name}</span>
        </div>
        
        <div className="header-actions">
          <div className="btn-dropdown">
            <svg aria-hidden="true" height="16" viewBox="0 0 16 16" version="1.1" width="16" fill="currentColor" style={{ marginRight: '4px' }}>
              <path fillRule="evenodd" d="M11.75 2.5a.75.75 0 100 1.5.75.75 0 000-1.5zm-2.25.75a2.25 2.25 0 113 2.122V10.63a2.251 2.251 0 11-1.5 0V5.372A2.25 2.25 0 019.5 3.25zM11 12a.75.75 0 100 1.5.75.75 0 000-1.5zm-5.25-1.25a.75.75 0 100 1.5.75.75 0 000-1.5zM7.25 12a2.25 2.25 0 11-3-2.122V3.75a.75.75 0 011.5 0v6.878A2.25 2.25 0 017.25 12z"></path>
            </svg>
            {repoInfo.branch}
          </div>
          <button 
            className="btn-primary btn-save-changes" 
            onClick={() => setShowConfirm(true)}
            disabled={modifiedCommitsCount === 0}
          >
            Save Changes
            {modifiedCommitsCount > 0 && <span className="badge">{modifiedCommitsCount}</span>}
          </button>
        </div>
      </header>

      <main className="main-content">
        {/* Timeline connector line behind the boxes */}
        <div className="timeline-line"></div>

        {/* Small clean title */}
        <div className="commits-header-row" style={{ paddingLeft: '48px' }}>
          <h2 className="commits-page-title" style={{ fontSize: '18px', fontWeight: '600' }}>Commits</h2>
        </div>

        {error && (
          <div className="error-banner" style={{ marginLeft: '48px' }}>
            <span className="error-icon">⚠️</span>
            <div className="error-content">
              <strong>Error:</strong> {error}
            </div>
            <button className="btn-close" onClick={() => setError(null)}>×</button>
          </div>
        )}

        {successResult && (
          <div className="success-overlay">
            <div className="success-modal">
              <div className="modal-header">
                <h2>🎉 Rewrite Successful</h2>
              </div>
              <div className="success-body">
                <span className="success-icon">✓</span>
                <p>{successResult.message}</p>
                {successResult.backup_path && (
                  <div className="backup-path-container">
                    <span className="backup-label">Safety Backup Created:</span>
                    <code className="backup-path">{successResult.backup_path}</code>
                  </div>
                )}
              </div>
              <div className="modal-footer">
                <button className="btn-primary" onClick={() => {
                  setSuccessResult(null)
                  fetchCommits()
                }}>
                  Dismiss & Reload History
                </button>
              </div>
            </div>
          </div>
        )}

        {showConfirm && (
          <div className="modal-overlay">
            <div className="confirm-modal">
              <div className="modal-header">
                <h2>Are you absolutely sure?</h2>
                <button className="btn-close" onClick={() => setShowConfirm(false)}>×</button>
              </div>
              <div className="modal-body">
                <p>
                  You are about to rewrite the history of your current branch. All descendants of the oldest modified commit will receive new commit hashes.
                </p>
                <div className="alert-box">
                  <strong>Warning:</strong> If you have already pushed these commits to a remote server, you will have to force-push (`git push --force`) to align them, which may disrupt other collaborators.
                </div>
                <p style={{ marginTop: '12px', fontSize: '11px', color: 'var(--color-fg-muted)' }}>
                  A safety backup of your `.git` folder will be created automatically before this operation.
                </p>
              </div>
              <div className="modal-footer">
                <button className="btn-secondary" onClick={() => setShowConfirm(false)} disabled={saving}>
                  Cancel
                </button>
                <button className="btn-primary btn-danger" onClick={handleSave} disabled={saving}>
                  {saving ? 'Rewriting History...' : 'Yes, Rewrite History'}
                </button>
              </div>
            </div>
          </div>
        )}

        {Object.keys(groupedCommits).map((dateStr) => (
          <div key={dateStr} className="commit-group">
            <div className="commit-group-title">
              Commits on {dateStr}
            </div>
            
            <div className="commit-box">
              {groupedCommits[dateStr].map((commit) => {
                const hasEdits = isModified(commit)
                const isOpen = editingHash === commit.hash
                const currentEdit = edits[commit.hash] || {
                  author_name: commit.author_name,
                  author_email: commit.author_email,
                  author_date: commit.author_date,
                  message: getFullMessage(commit),
                }

                const initialLetter = commit.author_name ? commit.author_name.charAt(0) : 'A'

                return (
                  <div key={commit.hash} className={`commit-row ${hasEdits ? 'modified' : ''} ${isOpen ? 'active' : ''}`}>
                    <div className="commit-row-summary">
                      <div className="commit-left">
                        <div className="commit-title-row">
                          <h3 className="commit-subject" onClick={() => handleStartEdit(commit)}>
                            {commit.subject}
                          </h3>
                          {hasEdits && <span className="modified-badge">Edited</span>}
                        </div>
                        <div className="commit-meta-row">
                          <span className="author-avatar">{initialLetter}</span>
                          <span className="author-name">{commit.author_name}</span>
                          <span className="commit-time">{getCommittedInfo(commit)}</span>
                        </div>
                        {!isOpen && commit.body && (
                          <pre className="commit-body-text">{commit.body}</pre>
                        )}
                      </div>
                      
                      <div className="commit-right">
                        <span className="commit-hash" title={commit.hash}>
                          {commit.hash.substring(0, 7)}
                        </span>
                        {!isOpen ? (
                          <button className="btn-secondary btn-sm" onClick={() => handleStartEdit(commit)}>
                            Edit
                          </button>
                        ) : (
                          <button className="btn-secondary btn-sm" onClick={() => setEditingHash(null)}>
                            Minimize
                          </button>
                        )}
                      </div>
                    </div>

                    {isOpen && (
                      <div className="commit-editor-panel">
                        <div className="editor-card">
                          <div className="editor-card-header">
                            <span>COMMIT DETAILS EDITOR</span>
                          </div>
                          
                          <div className="editor-card-body">
                            <div className="editor-grid">
                              <div className="form-group">
                                <label>Author Name</label>
                                <input
                                  type="text"
                                  value={currentEdit.author_name}
                                  onChange={(e) => handleInputChange(commit.hash, 'author_name', e.target.value)}
                                />
                              </div>
                              <div className="form-group">
                                <label>Author Email</label>
                                <input
                                  type="email"
                                  value={currentEdit.author_email}
                                  onChange={(e) => handleInputChange(commit.hash, 'author_email', e.target.value)}
                                />
                              </div>
                            </div>
                            
                            <div className="form-group">
                              <label>Date (ISO 8601)</label>
                              <input
                                type="text"
                                value={currentEdit.author_date}
                                onChange={(e) => handleInputChange(commit.hash, 'author_date', e.target.value)}
                              />
                            </div>
                            
                            <div className="form-group">
                              <label>Commit Message</label>
                              <textarea
                                rows={6}
                                value={currentEdit.message}
                                onChange={(e) => handleInputChange(commit.hash, 'message', e.target.value)}
                              />
                            </div>
                          </div>

                          {hasEdits && (
                            <div className="form-actions">
                              <button className="btn-secondary btn-sm btn-revert" onClick={() => handleRevert(commit.hash)}>
                                Revert Changes
                              </button>
                            </div>
                          )}
                        </div>
                      </div>
                    )}
                  </div>
                )
              })}
            </div>
          </div>
        ))}
      </main>
    </div>
  )
}

export default App
