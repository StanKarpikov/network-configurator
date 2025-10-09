#!/bin/bash

# Exit on errors
set -e

# Parse named parameters
while [[ $# -gt 0 ]]; do
    case "$1" in
        --src-python=*)
            SOURCE_DIR="${1#*=}"
            shift
            ;;
        --release-folder=*)
            RELEASE_FOLDER="${1#*=}"
            shift
            ;;
        *)
            echo "Unknown parameter: $1"
            echo "Usage: $0 --src-python=PATH --release-folder=PATH"
            exit 1
            ;;
    esac
done

if [ -z "$SOURCE_DIR" ] || [ -z "$RELEASE_FOLDER" ]; then
    echo "Usage: $0 --src-python=PATH --release-folder=PATH"
    exit 1
fi

SOURCE_DIR="$(cd "$SOURCE_DIR" && pwd)"
RELEASE_FOLDER="$(cd "$RELEASE_FOLDER" && pwd)"

TARGET_DIR="$RELEASE_FOLDER/network-configurator"

mkdir -p "$TARGET_DIR"

rsync -avm --include='*.py' --exclude='*' "$SOURCE_DIR/" "$TARGET_DIR/"

cp "$SOURCE_DIR/../network-configuration.default.conf" "$TARGET_DIR/"

cp -r "$SOURCE_DIR/../static" "$TARGET_DIR/"

echo "Copied all Python files from $SOURCE_DIR to $TARGET_DIR"
