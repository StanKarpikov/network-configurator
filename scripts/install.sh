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
        --destination-folder=*)
            RELEASE_DIR="${1#*=}"
            shift
            ;;
        *)
            echo "Unknown parameter: $1"
            echo "Usage: $0 --src-python=PATH --destination-folder=PATH"
            exit 1
            ;;
    esac
done

if [ -z "$SOURCE_DIR" ] || [ -z "$RELEASE_DIR" ]; then
    echo "Usage: $0 --src-python=PATH --destination-folder=PATH"
    exit 1
fi

SOURCE_DIR="$(cd "$SOURCE_DIR" && pwd)"
RELEASE_DIR="$(cd "$RELEASE_DIR" && pwd)"

TARGET_DIR="$RELEASE_DIR/network-configurator"

mkdir -p "$TARGET_DIR"

rsync -avm --include='*.py' --exclude='*' "$SOURCE_DIR/" "$TARGET_DIR/"

cp "$SOURCE_DIR/../network-configuration.default.conf" "$TARGET_DIR/"

cp -r "$SOURCE_DIR/../static" "$TARGET_DIR/"

echo "Copied all Python files from $SOURCE_DIR to $TARGET_DIR"
