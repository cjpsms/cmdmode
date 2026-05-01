#!/usr/bin/env bash
set -e

echo "=== cmdmode installer ==="

# 1. dependency
if ! python3 -c "import evdev" 2>/dev/null; then
    echo "Installing python-evdev..."
    sudo pacman -S --noconfirm python-evdev
fi

# 2. input group
if ! groups | grep -q input; then
    echo "Adding $USER to input group..."
    sudo usermod -aG input "$USER"
    echo "⚠ Re-login required for group change to take effect"
fi

# 3. config
mkdir -p ~/.config/cmdmode
if [ ! -f ~/.config/cmdmode/commands.json ]; then
    cp "$(dirname "$0")/commands.json" ~/.config/cmdmode/commands.json
    echo "Config installed at ~/.config/cmdmode/commands.json"
else
    echo "Config already exists, skipping"
fi

# 4. script
mkdir -p ~/.local/bin
cp "$(dirname "$0")/cmdmode.py" ~/.local/bin/cmdmode
chmod +x ~/.local/bin/cmdmode

# 5. systemd user service
mkdir -p ~/.config/systemd/user
cat > ~/.config/systemd/user/cmdmode.service << 'EOF'
[Unit]
Description=cmdmode — triple Super tap command launcher
After=graphical-session.target
StartLimitBurst=0

[Service]
ExecStartPre=/bin/sleep 3
ExecStart=%h/.local/bin/cmdmode
Restart=on-failure
RestartSec=5

[Install]
WantedBy=graphical-session.target
EOF

systemctl --user daemon-reload
systemctl --user enable --now cmdmode.service

echo ""
echo "=== Done ==="
echo "Service status: systemctl --user status cmdmode"
echo "Edit commands:  ~/.config/cmdmode/commands.json"
echo "Logs:           journalctl --user -u cmdmode -f"
