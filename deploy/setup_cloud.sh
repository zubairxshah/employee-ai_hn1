#!/bin/bash
# Oracle Cloud VM Bootstrap Script
# Sets up Docker, clones repo, and starts the cloud agent

set -e

echo "=========================================="
echo "AI Employee - Cloud Setup"
echo "=========================================="

# Update system
echo "[1/6] Updating system..."
sudo apt-get update && sudo apt-get upgrade -y

# Install Docker
echo "[2/6] Installing Docker..."
if ! command -v docker &> /dev/null; then
    curl -fsSL https://get.docker.com -o get-docker.sh
    sudo sh get-docker.sh
    sudo usermod -aG docker $USER
    rm get-docker.sh
    echo "Docker installed. You may need to log out and back in."
fi

# Install Docker Compose
echo "[3/6] Installing Docker Compose..."
if ! command -v docker-compose &> /dev/null; then
    sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" \
        -o /usr/local/bin/docker-compose
    sudo chmod +x /usr/local/bin/docker-compose
fi

# Install git
echo "[4/6] Installing git..."
sudo apt-get install -y git

# Clone repo
echo "[5/6] Cloning repository..."
REPO_DIR="$HOME/ai-employee"
if [ ! -d "$REPO_DIR" ]; then
    echo "Please clone your repository to $REPO_DIR"
    echo "  git clone <your-repo-url> $REPO_DIR"
    echo ""
    echo "Then copy cloud.env.example to cloud.env and configure:"
    echo "  cd $REPO_DIR/deploy"
    echo "  cp cloud.env.example cloud.env"
    echo "  nano cloud.env"
else
    echo "Repository already exists at $REPO_DIR"
fi

# Setup cron for backups
echo "[6/6] Setting up backup cron..."
BACKUP_SCRIPT="$REPO_DIR/deploy/backup_odoo.sh"
if [ -f "$BACKUP_SCRIPT" ]; then
    chmod +x "$BACKUP_SCRIPT"
    # Add daily backup at 2 AM
    (crontab -l 2>/dev/null; echo "0 2 * * * $BACKUP_SCRIPT") | sort -u | crontab -
    echo "Backup cron job added (daily at 2 AM)"
fi

echo ""
echo "=========================================="
echo "Setup complete!"
echo ""
echo "Next steps:"
echo "  1. cd $REPO_DIR/deploy"
echo "  2. cp cloud.env.example cloud.env"
echo "  3. Edit cloud.env with your credentials"
echo "  4. docker-compose -f docker-compose.cloud.yml up -d"
echo "=========================================="
