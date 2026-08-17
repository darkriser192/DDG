# Git Notes — Refactor Safety Net

A short reference for solo work on this project. The goal is simple: **make every
refactor reversible.** If you can undo it, it is an experiment, not a risk.

Run all commands in the project folder (`D:\DDG`).

---

## 1. One-time setup

| Command | What it does |
|---|---|
| `git init` | Start tracking this folder. Creates a hidden `.git` directory. Do this once. |
| `git add -A` | Stage all files. "Staged" means selected for the next snapshot. |
| `git commit -m "First commit"` | Save the snapshot. This is your first restore point. |
| `git config user.name "Your Name"` | Set the author name (once per machine). |
| `git config user.email "you@example.com"` | Set the author email (once per machine). |

**Make a `.gitignore` file first.** Put this in it:

```
__pycache__/
*.pyc
imgui.ini
.venv/
```

Large STL files are optional. Git stores each version of a binary in full, so the
repository grows fast. Keep `rabbit-low-poly.stl` (the app pre-loads it). Consider
ignoring the large ones.

---

## 2. The daily loop

| Command | What it does |
|---|---|
| `git status` | Show which files changed. Run this first, always. |
| `git diff` | Show the changed lines you have **not** staged yet. |
| `git diff --staged` | Show the changed lines you **have** staged. |
| `git add -A` | Stage all changes. |
| `git add ddg_objects.py` | Stage one file only. |
| `git commit -m "Message"` | Save a snapshot of the staged changes. |
| `git log --oneline` | List past commits, newest first. Each has a short ID (a "hash"). |

**Commit often.** A commit costs nothing and each one is a point you can return to.
Write the message as what the change does: `"Rename Facet* to Face* in MeshObject"`.

---

## 3. Undo — the important part

| Command | What it does |
|---|---|
| `git restore ddg_objects.py` | Throw away your changes to one file. Back to the last commit. |
| `git restore .` | Throw away **all** uncommitted changes. |
| `git restore --source=HEAD~2 ddg_objects.py` | Get one file back as it was 2 commits ago. Other files stay as they are. |
| `git stash` | Park all current changes and get a clean folder. Nothing is lost. |
| `git stash pop` | Bring the parked changes back. |
| `git reset --soft HEAD~1` | Undo the last **commit**, but keep the file changes. Use when the message was wrong. |
| `git revert <hash>` | Undo an old commit by adding a new commit that reverses it. Safe — it deletes no history. |

**Destructive — read before you use it:**

| Command | What it does |
|---|---|
| `git reset --hard HEAD` | Delete all uncommitted changes and return to the last commit. **Not recoverable.** |

Older tutorials write `git checkout -- <file>` instead of `git restore <file>`.
They do the same thing. `restore` is the newer and clearer name.

---

## 4. Branches — for a large refactor

A branch is a separate line of work. The main line stays untouched until you decide
to merge.

| Command | What it does |
|---|---|
| `git switch -c refactor/meshobject` | Create a branch and move to it. |
| `git switch main` | Go back to the main line. |
| `git branch` | List branches. The `*` marks where you are. |
| `git diff main` | Show every difference between this branch and `main`. |
| `git merge refactor/meshobject` | Bring the branch work into the branch you are on. |
| `git branch -d refactor/meshobject` | Delete the branch after you merge it. |

Older tutorials write `git checkout -b name`. `git switch -c name` is the newer name.

---

## 5. Recipe for the MeshObject refactor

1. `git status` — confirm the folder is clean. Commit anything outstanding first.
2. `git switch -c refactor/meshobject` — work on a branch.
3. Make **one** change. Example: fix the class docstring.
4. Run the app. Click "Compute Vertex Error". The `TrimeshVertexDefect` assert
   confirms the math still agrees with trimesh.
5. `git add -A` then `git commit -m "Fix MeshObject docstring"`.
6. Repeat steps 3 to 5 for each change.
7. If a change goes wrong: `git restore .` and try again. You lose only step 3.
8. When it works: `git switch main` then `git merge refactor/meshobject`.

**The rule:** commit after each change that leaves the app working. Then a mistake
costs you one step, not one day.

---

## 6. Reading history

| Command | What it does |
|---|---|
| `git log --oneline -10` | The last 10 commits. |
| `git show <hash>` | Show everything one commit changed. |
| `git log --oneline ddg_objects.py` | Show only the commits that touched one file. |
| `git diff HEAD~1 HEAD` | Compare the last commit to the one before it. |

`HEAD` means "where I am now". `HEAD~1` is one commit back, `HEAD~2` is two, and so on.
