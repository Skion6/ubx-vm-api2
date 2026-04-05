#!/bin/bash
set -e
apt-get update -y
apt-get install -y aqemu
apt-get install -y neofetch

sleep 1
rm /usr/share/applications/aqemu.desktop
cp /installable-apps/aqemu.desktop /usr/share/applications/aqemu.desktop