# leavehub — git & github guide

Everything you need to do with git and GitHub for this project, in order. Run all commands
from the `leavehub/` directory (the one with `manage.py`). Each project is its own repo and
becomes its own GitHub repo.

The workflow below is **one feature branch per phase, merged through a Pull Request**. It's
more steps than committing straight to `main`, but it's how real teams work and it's worth
practising on these projects.

## What's already set up (don't redo)

- Git is installed and your identity is configured:
  `Hemannbrl <hemann.brl@gmail.com>`.
- This folder already has a repo (`git init` was run) on branch `main`.
- The GitHub CLI `gh` is installed and you're logged in as **hemannbrl** (HTTPS).
- `.gitignore` already excludes `.env`, `.venv/`, `db.sqlite3`, and `__pycache__/` — so
  secrets and junk won't be committed.

Confirm any of it:
```bash
git config user.name          # Hemannbrl
git config user.email         # hemann.brl@gmail.com
gh auth status                # logged in as hemannbrl
git status                    # branch + what's changed
```

## One time — first commit and create the GitHub repo

The Phase 0 scaffold goes onto `main` first. Before the first commit, make sure no secret
is staged:
```bash
git status                    # .env and .venv/ must NOT appear
git check-ignore .env .venv   # should print both -> they're ignored
```
Commit it and create the repo:
```bash
git add -A
git commit -m "initial Django scaffold for leavehub"
gh repo create leavehub --private --source=. --remote=origin --push
```
That creates `github.com/hemannbrl/leavehub`, wires up `origin`, and pushes `main`. Make it
public later for your portfolio with
`gh repo edit --visibility public --accept-visibility-change-consequences`.

Confirm:
```bash
git remote -v                 # origin -> github.com/hemannbrl/leavehub
gh browse                     # open it in the browser
```

---

## The per-phase workflow (do this for every phase)

### 1. Get the latest code
Start each phase from an up-to-date `main`:
```bash
git checkout main
git pull origin main
```

### 2. Create a feature branch
Name it after the phase you're about to build:
```bash
git checkout -b feature/phase-1-roles
```
(Pattern: `feature/phase-<number>-<short-name>`, e.g. `feature/phase-5-leave-request`.)

### 3. Work on the feature
As you code, see what changed:
```bash
git status                    # which files changed
git diff                      # the exact line-by-line changes
```

### 4. Stage your changes
Stage everything:
```bash
git add .
```
Or stage specific files:
```bash
git add leave/models.py
git add leave/permissions.py
```

### 5. Commit
Use the commit message printed at the end of the phase in `BUILD_ORDER.md`:
```bash
git commit -m "add leave type and balance models"
```
You can make several commits within a phase — commit each logical step rather than one giant
blob.

### 6. Push the branch
First push of a new branch sets its upstream with `-u`:
```bash
git push -u origin feature/phase-1-roles
```
After that, pushing more commits on the same branch is just:
```bash
git push
```

### 7. Keep your branch up to date (only if needed)
For a solo repo `main` rarely moves while you work, so you can usually skip this. If `main`
did change, bring it into your branch:
```bash
git checkout main
git pull origin main

git checkout feature/phase-1-roles
git merge main
```
Some people prefer rebasing instead:
```bash
git fetch origin
git rebase origin/main
```
Pick one and stay consistent.

### 8. Before opening a PR
Make sure tests pass and the tree is clean:
```bash
python manage.py test
git status                    # should say: nothing to commit, working tree clean
git push                      # push any last commits
```

### 9. Open the PR and merge
```bash
gh pr create --fill                       # title/body from your commits
gh pr merge --squash --delete-branch      # merge into main, delete the branch
git checkout main
git pull origin main                      # bring the merge back locally
```
(You can also open and merge the PR from the GitHub website — `gh browse` to get there.)

Then go back to step 1 for the next phase.

---

## Checking where things are

"Did it push? What's on GitHub right now?"
```bash
git status                    # clean? which branch? ahead/behind?
git branch                    # local branches (* marks current)
git branch -vv                # branches + their upstream + ahead/behind
git log --oneline             # local commit history
git log origin/main --oneline # what main on GitHub actually has
gh pr list                    # open pull requests
gh pr status                  # the PR for your current branch
gh browse                     # open the repo in the browser
```

## The commands you'll use most often
```bash
git checkout main
git pull origin main
git checkout -b feature/phase-1-roles

git status
git diff

git add .
git commit -m "add leave type and balance models"

git push -u origin feature/phase-1-roles
```

After the first push on a branch, the day-to-day loop is usually just:
```bash
git status
git add .
git commit -m "describe what changed"
git push
```

## Fixing common mistakes

- **Forgot a file in the last commit** (not pushed): `git add file && git commit --amend --no-edit`
- **Typo in the last commit message** (not pushed): `git commit --amend -m "the right message"`
- **Staged something by accident:** `git restore --staged path/to/file`
- **Undo the last commit, keep the changes:** `git reset --soft HEAD~1`
- **On `main` by mistake with uncommitted work:** `git stash`, then
  `git checkout -b feature/...`, then `git stash pop`.
- **Accidentally committed `.env`:** it's gitignored, so
  `git rm --cached .env && git commit -m "stop tracking .env"`. It's still in history, so
  rotate the secret.
- **See what a commit changed:** `git show <hash>`.

> Don't `--amend` or `reset` commits you've already pushed and shared. On a solo repo it's
> recoverable, but build the habit now.

## A word on secrets

`.env` holds a real `DJANGO_SECRET_KEY`. It's gitignored and must never be committed. If a
secret ever lands in a commit, treat it as leaked and rotate it — git keeps history.

## Cheat sheet

| goal | command |
|------|---------|
| latest main | `git checkout main && git pull origin main` |
| new branch | `git checkout -b feature/phase-x-name` |
| what changed | `git status` / `git diff` |
| stage | `git add .` |
| commit | `git commit -m "message"` |
| first push | `git push -u origin <branch>` |
| later pushes | `git push` |
| open PR | `gh pr create --fill` |
| merge PR | `gh pr merge --squash --delete-branch` |
| what's on GitHub | `git log origin/main --oneline` |
| open in browser | `gh browse` |
