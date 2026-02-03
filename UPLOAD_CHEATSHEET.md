# GitHub Upload Cheat Sheet

## One-Command Upload

```bash
cd /Users/burakbulut/projects/pipewatch && \
git init && \
git add . && \
git commit -m "Initial commit: Pipewatch v0.1.0" && \
git branch -M main && \
git remote add origin https://github.com/YOUR_USERNAME/pipewatch.git && \
git push -u origin main
```

## Step by Step

| Step | Command | Purpose |
|------|---------|---------|
| 1 | `cd /Users/burakbulut/projects/pipewatch` | Go to project |
| 2 | `git init` | Initialize git |
| 3 | `git add .` | Stage files |
| 4 | `git commit -m "message"` | Commit |
| 5 | `git remote add origin URL` | Link GitHub |
| 6 | `git push -u origin main` | Upload |

## Prerequisites

1. GitHub account: https://github.com/signup
2. Create repository: https://github.com/new
3. Personal Access Token: https://github.com/settings/tokens

## Verify Upload

```bash
# Check remote
git remote -v

# Check status
git status

# View log
git log --oneline
```

## Fix Common Issues

| Problem | Solution |
|---------|----------|
| "Permission denied" | Use Personal Access Token as password |
| "Repository not found" | Create repo on GitHub first |
| "Remote already exists" | `git remote remove origin` |
| "Updates rejected" | `git push --force` (initial only) |

## After Upload Checklist

- [ ] Check: https://github.com/YOUR_USERNAME/pipewatch
- [ ] Enable Actions (if not auto-enabled)
- [ ] Add topics/tags to repository
- [ ] Create release v0.1.0
- [ ] Test: `pip install git+https://github.com/YOUR_USERNAME/pipewatch.git`
