#!/bin/bash

# Exit on errors
set -e

if [ "$#" -ne 2 ]; then
    echo "Usage: $0 <source_folder> <release_folder>"
    exit 1
fi

SOURCE_DIR="$1"
RELEASE_DIR="$2"

SOURCE_DIR="$(cd "$SOURCE_DIR" && pwd)"
RELEASE_DIR="$(cd "$RELEASE_DIR" && pwd)"

TARGET_DIR="$RELEASE_DIR/network-configurator"

mkdir -p "$TARGET_DIR"

# Copy all Python files from source to the target directory
find "$SOURCE_DIR" -maxdepth 1 -type f -name "*.py" -exec cp {} "$TARGET_DIR" \;

echo "Copied all Python files from $SOURCE_DIR to $TARGET_DIR"
