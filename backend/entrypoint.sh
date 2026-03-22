#!/bin/bash
set -e

echo "Installing runtime dependencies..."
apt-get update && apt-get install -y --no-install-recommends \
    libreoffice-writer libreoffice-calc libreoffice-impress \
    poppler-utils ghostscript \
    fonts-liberation \
    fonts-dejavu \
    fonts-noto \
    && rm -rf /var/lib/apt/lists/*

echo "ttf-mscorefonts-installer msttcorefonts/accepted-msa-eula select true" | debconf-set-selections
apt-get install -y --no-install-recommends ttf-mscorefonts-installer

exec "$@"