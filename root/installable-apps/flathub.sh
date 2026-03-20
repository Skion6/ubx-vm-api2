#!/bin/bash
set -e
echo "**** install flatpak and flathub store ****"
apt install -y flatpak gnome-software-plugin-flatpak
flatpak remote-add --if-not-exists flathub https://dl.flathub.org/repo/flathub.flatpakrepo
