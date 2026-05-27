# Git History Writer (`git-writer`) ✍️

A sleek, premium, developer-focused standalone web interface designed to view and rewrite your Git repository history with absolute safety and visual ease.

---

## 💡 Motivation: Why does this exist?

We've all been there:
- You committed a batch of changes only to realize a typo in the second-to-last commit message.
- You committed using your personal email instead of your work email (or vice versa).
- You want to add trailing `Co-Authored-By` metadata to historical commits.
- You need to shift commit dates to align with actual task delivery times.

### The Pain of Traditional Rebase
Git's native `git commit --amend` only works on the single latest commit. To edit commits further back in history, you are forced to run:
```bash
git rebase -i HEAD~n
```
This drops you into a terminal editor, forces you to pick/edit lines, and frequently results in stressful merge conflicts, complex bash states, and the risk of corrupting your history if you make a mistake.

### The `git-writer` Solution
`git-writer` replaces the intimidation of terminal rebases with a beautiful, high-fidelity **GitHub Primer-themed standalone web interface**. You can view your entire repository timeline in one fluid edge-to-edge view, click **Edit** on any commit, and modify:
1. **Commit Messages** (including multi-line descriptions and co-author footers)
2. **Author Names**
3. **Author Emails**
4. **Commit Dates** (using a simple visual picker or typing)

It executes atomic Git history rewrites behind the scenes and **automatically backs up your repository** before every single action, keeping you 100% safe.

---

## ⚡ Zero-Installation Quickstart

Thanks to the speed of [Astral `uv`](https://github.com/astral-sh/uv), you can run `git-writer` instantly on any local repository **without installing anything** on your system:

```bash
uvx --from git+https://github.com/dev-ansung/git-writer git-writer [path-to-your-repo]
```

*If no path is specified, it defaults to the current working directory.*

Once running, simply open **`http://127.0.0.1:8000`** in your browser to begin editing!

---

## 🛡️ Uncompromising Safety First

Rewriting Git history is an invasive operation. That's why `git-writer` is built with a **fail-safe backup mechanism**:

- **Automatic Backups:** Before performing any history rewrite, `git-writer` compresses and copies your current `.git` directory to `.git/git-writer-backups/backup_[timestamp].tar.gz`.
- **Easy Reversion:** If you make a mistake, change your mind, or encounter any conflict, your original repository state can be fully restored in seconds.
- **Safety Logs:** The CLI outputs the exact path of the safety backup file before executing every rewrite.

---

## 🛠️ Built with a Premium Developer Aesthetic

`git-writer` is designed to feel like a premium, native developer tool:
- **GitHub Primer Aesthetic:** A clean, crisp, minimalist light theme inspired by GitHub's official design system.
- **Fully Fluid Edge-to-Edge Layout:** Optimizes wide-screen displays, presenting a wide, spacious timeline layout that fits long commit descriptions perfectly.
- **Subpixel-Perfect Timeline Gutter:** A beautifully aligned commit connector timeline built with pure responsive CSS grid sizing (no fragile absolute pixel offsets).

---

## 🔧 Local Development

If you'd like to run `git-writer` from source or contribute to its development:

### Prerequisites
- Install [uv](https://github.com/astral-sh/uv)
- Install [Node.js](https://nodejs.org/) (for building the frontend)

### 1. Clone the repository
```bash
git clone https://github.com/dev-ansung/git-writer.git
cd git-writer
```

### 2. Build the Frontend
Build the responsive React assets directly into the Python package directory:
```bash
cd frontend
npm install
npm run build
cd ..
```

### 3. Run the Backend Server
Launch the FastAPI service targeting any local git repository:
```bash
uv run git-writer /path/to/your/git-repo
```

---

## 📄 License

This project is licensed under the MIT License.
