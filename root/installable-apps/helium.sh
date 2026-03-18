echo "**** install helium browser ****"
apt install -y wget libfuse2
# Download latest Helium AppImage from GitHub (imputnet/helium-linux)
HELIUM_URL=$(wget -qO- "https://api.github.com/repos/imputnet/helium-linux/releases/latest" | jq -r '.assets[] | select(.name | endswith("x86_64.AppImage")) | .browser_download_url')
if [ -z "$HELIUM_URL" ]; then
    # Fallback to known version
    HELIUM_URL="https://github.com/imputnet/helium-linux/releases/download/0.10.5.1/helium-0.10.5.1-x86_64.AppImage"
fi
wget -q -O /usr/local/bin/helium "$HELIUM_URL"
chmod +x /usr/local/bin/helium
# Create desktop entry
mkdir -p /usr/share/applications
cat > /usr/share/applications/helium.desktop << 'EOF'
[Desktop Entry]
Name=Helium Browser
Comment=Privacy-focused web browser
Exec=/usr/local/bin/helium --no-sandbox %U
Terminal=false
Type=Application
Icon=web-browser
Categories=Network;WebBrowser;
MimeType=text/html;text/xml;application/xhtml+xml;
EOF
