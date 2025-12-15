#!/bin/bash

# E-Paper Automation Setup Script
# This script sets up the complete automation system

set -e  # Exit on error

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║       📰 E-NEWSPAPER AUTOMATION SETUP                          ║"
echo "║       Setting up GitHub Actions workflow...                    ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Function to print colored output
print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

# Check if git is installed
if ! command -v git &> /dev/null; then
    print_error "Git is not installed. Please install git first."
    exit 1
fi

print_success "Git found"

# Create directory structure
print_info "Creating directory structure..."

mkdir -p .github/workflows
mkdir -p e-paper

print_success "Directories created"

# Create initial history file
print_info "Initializing download history..."

cat > download_history.json << 'EOF'
{
  "downloads": []
}
EOF

print_success "History file created"

# Create README if it doesn't exist
if [ ! -f README.md ]; then
    print_info "Creating README.md..."
    
    cat > README.md << 'EOF'
# 📰 E-Newspaper Auto-Downloader

Automated daily download of The Hindu and Indian Express newspapers.

## Quick Start

1. Add Discord webhook URL to repository secrets as `DISCORD_WEBHOOK_URL`
2. Enable GitHub Pages (Settings → Pages → Source: gh-pages branch)
3. Go to Actions tab and enable workflows
4. Run the workflow manually or wait for scheduled run

## Features

- ✅ Automated daily downloads at 6 AM IST
- 📦 PDF compression to save storage
- 📁 Organized monthly folders
- 🗑️ Auto cleanup of old files
- 📨 Discord notifications
- 🌐 GitHub Pages hosting

## Configuration

Edit `config.json` to customize newspapers, schedule, and settings.

## Manual Run

Go to Actions → Download E-Newspapers → Run workflow

## Support

Open an issue for questions or problems.
EOF
    
    print_success "README.md created"
else
    print_warning "README.md already exists, skipping"
fi

# Create .gitignore
print_info "Creating .gitignore..."

cat > .gitignore << 'EOF'
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
venv/
env/
.env

# IDE
.vscode/
.idea/
*.swp
*.swo

# Temporary files
temp_*.pdf
*.tmp

# OS
.DS_Store
Thumbs.db

# Don't ignore the folders and files we need
!e-paper/
!download_history.json
EOF

print_success ".gitignore created"

# Create config.json if it doesn't exist
if [ ! -f config.json ]; then
    print_info "Creating config.json..."
    
    cat > config.json << 'EOF'
{
  "newspapers": {
    "The Hindu": {
      "code": "TH-+Delhi",
      "display_name": "The Hindu",
      "enabled": true
    },
    "Indian Express": {
      "code": "IE-+Delhi",
      "display_name": "Indian Express",
      "enabled": true
    }
  },
  "settings": {
    "cleanup_buffer_days": 7,
    "compression_enabled": true,
    "retry_attempts": 3
  }
}
EOF
    
    print_success "config.json created"
else
    print_warning "config.json already exists, skipping"
fi

# Initialize git if not already initialized
if [ ! -d .git ]; then
    print_info "Initializing git repository..."
    git init
    print_success "Git initialized"
else
    print_info "Git already initialized"
fi

# Check if files need to be added
print_info "Checking git status..."

if [ -n "$(git status --porcelain)" ]; then
    print_info "Adding files to git..."
    
    git add .github/workflows/
    git add newspaper_downloader.py 2>/dev/null || print_warning "newspaper_downloader.py not found yet"
    git add requirements.txt 2>/dev/null || print_warning "requirements.txt not found yet"
    git add download_history.json
    git add index.html 2>/dev/null || print_warning "index.html not found yet"
    git add config.json
    git add README.md
    git add .gitignore
    git add e-paper/
    
    print_success "Files staged for commit"
else
    print_info "No new files to stage"
fi

echo ""
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║                    SETUP COMPLETE! ✓                           ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""
print_success "Repository structure created successfully!"
echo ""
echo "📋 NEXT STEPS:"
echo ""
echo "1. Ensure all Python files are in the repository:"
echo "   - newspaper_downloader.py"
echo "   - requirements.txt"
echo "   - index.html"
echo ""
echo "2. Commit and push to GitHub:"
echo "   ${BLUE}git commit -m \"Initial setup - E-Paper automation\"${NC}"
echo "   ${BLUE}git remote add origin YOUR_REPO_URL${NC}"
echo "   ${BLUE}git branch -M main${NC}"
echo "   ${BLUE}git push -u origin main${NC}"
echo ""
echo "3. Add Discord Webhook Secret:"
echo "   - Go to: Settings → Secrets and variables → Actions"
echo "   - Click: New repository secret"
echo "   - Name: DISCORD_WEBHOOK_URL"
echo "   - Value: Your Discord webhook URL"
echo ""
echo "4. Enable GitHub Pages:"
echo "   - Go to: Settings → Pages"
echo "   - Source: Deploy from a branch"
echo "   - Branch: gh-pages → /root"
echo "   - Click Save"
echo ""
echo "5. Enable GitHub Actions:"
echo "   - Go to: Actions tab"
echo "   - Click: \"I understand my workflows, go ahead and enable them\""
echo ""
echo "6. Test the workflow:"
echo "   - Actions → Download E-Newspapers → Run workflow"
echo ""
echo "🎉 Your automation will run daily at 6:00 AM IST!"
echo ""
