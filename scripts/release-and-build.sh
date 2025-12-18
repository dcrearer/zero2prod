#!/bin/bash
set -e

echo "Running cargo release..."
cargo release minor --no-publish --execute

echo "Building debug binary with new version..."
cargo build

echo "Building container image..."
VERSION=$(cargo metadata --format-version 1 | jq -r '.packages[0].version')
podman build -t zero2prod:$VERSION .
podman tag zero2prod:$VERSION zero2prod:latest

echo "✅ Released version $VERSION"
echo "✅ Built binary: target/debug/zero2prod (version $VERSION)"
echo "✅ Built images: zero2prod:$VERSION, zero2prod:latest"
