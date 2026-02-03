# Upload Pipewatch to GitHub - Complete Workflow

This guide walks you through uploading the pipewatch repository to GitHub.

---

## Step 1: Create a GitHub Repository

### Option A: Using GitHub Web Interface

1. Go to https://github.com/new
2. Enter repository details:
   - **Repository name**: `pipewatch`
   - **Description**: `Pipeline observability for legacy Slurm-based bioinformatics workflows`
   - **Visibility**: Public (or Private)
   - **Initialize**: ❌ DO NOT check "Add a README" (we already have one)
   - **Add .gitignore**: ❌ DO NOT select (we already have one)
   - **Add license**: ❌ DO NOT select (we already have one)
3. Click **"Create repository"**

### Option B: Using GitHub CLI (if installed)

```bash
# Install gh if not already: https://cli.github.com/
gh auth login
gh repo create pipewatch \
  --public \
  --description "Pipeline observability for legacy Slurm-based bioinformatics workflows" \
  --source=. \
  --remote=origin
```

---

## Step 2: Initialize Git Locally (if not already)

```bash
# Navigate to your project
cd /Users/burakbulut/projects/pipewatch

# Check if git is already initialized
ls -la .git

# If .git doesn't exist, initialize it
git init

# Configure git (if not already configured)
git config user.name "Your Name"
git config user.email "your.email@example.com"
```

---

## Step 3: Stage All Files

```bash
# Check current status
git status

# Add all files
git add .

# Verify what will be committed
git status
```

You should see all the files listed in green (staged).

---

## Step 4: Commit the Files

```bash
# Create initial commit
git commit -m "Initial commit: Pipewatch v0.1.0

Features:
- obsrun: Bash wrapper for command observability
- pipewatch CLI: wrap, run, and report commands
- Event collection with NDJSON output
- HTML/JSON report generation
- SLURM environment integration
- Run-to-run comparison

Includes:
- 36 unit tests
- 3 example workflows
- CI/CD configuration
- Docker support"
```

---

## Step 5: Connect to GitHub Remote

```bash
# Add the GitHub remote (replace YOUR_USERNAME with your GitHub username)
git remote add origin https://github.com/YOUR_USERNAME/pipewatch.git

# Verify remote was added
git remote -v
```

**Output should show:**
```
origin  https://github.com/YOUR_USERNAME/pipewatch.git (fetch)
origin  https://github.com/YOUR_USERNAME/pipewatch.git (push)
```

---

## Step 6: Push to GitHub

```bash
# Push to main branch
git branch -M main
git push -u origin main
```

**Enter your credentials when prompted:**
- Username: Your GitHub username
- Password: Your GitHub Personal Access Token (not your password!)
  - Create one at: https://github.com/settings/tokens
  - Required scopes: `repo`

---

## Step 7: Verify Upload

### Check GitHub Repository

1. Go to: `https://github.com/YOUR_USERNAME/pipewatch`
2. Verify all files are present:
   - [ ] README.md
   - [ ] src/pipewatch/
   - [ ] tests/
   - [ ] examples/
   - [ ] .github/workflows/ci.yml

### Clone Test (Optional)

```bash
# Test by cloning to a different location
cd /tmp
git clone https://github.com/YOUR_USERNAME/pipewatch.git pipewatch_test
ls pipewatch_test
```

---

## Step 8: Enable GitHub Actions

1. Go to: `https://github.com/YOUR_USERNAME/pipewatch/actions`
2. Click **"I understand my workflows, go ahead and enable them"**
3. The CI workflow will run automatically

---

## Step 9: Add Repository Topics (Optional)

1. Go to repository main page
2. Click the gear icon next to "About"
3. Add topics:
   - `bioinformatics`
   - `slurm`
   - `hpc`
   - `pipeline`
   - `observability`
   - `monitoring`
   - `python`
   - `bash`
4. Click **"Save changes"**

---

## Step 10: Create a Release (Optional)

```bash
# Tag the release
git tag -a v0.1.0 -m "Release v0.1.0 - Initial release"
git push origin v0.1.0
```

Or via GitHub:
1. Go to: `https://github.com/YOUR_USERNAME/pipewatch/releases`
2. Click **"Create a new release"**
3. Enter `v0.1.0` as tag
4. Add release notes
5. Click **"Publish release"**

---

## Quick Reference: All Commands

```bash
# Complete workflow in one go:
cd /Users/burakbulut/projects/pipewatch
git init
git add .
git commit -m "Initial commit: Pipewatch v0.1.0"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/pipewatch.git
git push -u origin main
```

---

## Troubleshooting

### Issue: "Repository not found"

**Solution**: Make sure you created the repository on GitHub first (Step 1).

### Issue: "Permission denied"

**Solution**: Use Personal Access Token instead of password:
1. Go to https://github.com/settings/tokens
2. Generate new token (classic)
3. Select `repo` scope
4. Use token as password when pushing

### Issue: "fatal: remote origin already exists"

**Solution**:
```bash
git remote remove origin
git remote add origin https://github.com/YOUR_USERNAME/pipewatch.git
```

### Issue: "Updates were rejected"

**Solution**:
```bash
# Force push (only for initial upload!)
git push -u origin main --force
```

---

## After Upload - Next Steps

### Verify CI Works

1. Go to `https://github.com/YOUR_USERNAME/pipewatch/actions`
2. Wait for the first workflow run
3. Should show green checkmark when complete

### Test Installation from GitHub

```bash
# Test pip install from git
pip install git+https://github.com/YOUR_USERNAME/pipewatch.git

# Verify
pipewatch --version
```

### Share the Project

Update these files with your GitHub URL:
- `pyproject.toml`: Update `[project.urls]` section
- `README.md`: Update badge URLs and installation instructions

Example update to `pyproject.toml`:
```toml
[project.urls]
Homepage = "https://github.com/YOUR_USERNAME/pipewatch"
Documentation = "https://github.com/YOUR_USERNAME/pipewatch#readme"
Repository = "https://github.com/YOUR_USERNAME/pipewatch"
Issues = "https://github.com/YOUR_USERNAME/pipewatch/issues"
```

---

## Done! 🎉

Your pipewatch repository is now on GitHub!

**Repository URL**: `https://github.com/YOUR_USERNAME/pipewatch`

**What to do next**:
- [ ] Enable GitHub Actions
- [ ] Add repository topics
- [ ] Create a release
- [ ] Share with colleagues
- [ ] Add to your CV/LinkedIn
