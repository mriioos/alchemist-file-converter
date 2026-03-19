#!/bin/sh
set -e

echo "Installing runtime dependencies..."
apk add --no-cache \
    libreoffice \
    poppler-utils \
    ghostscript

exec "$@"
