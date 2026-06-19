#!/bin/bash
# Build Next.js landing page → Django static files
set -e

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LANDING="$ROOT/landingpage_source"
STATIC="$ROOT/static"

echo "▶ Building Next.js landing page..."
cd "$LANDING"
npm run build

echo "▶ Copying assets to Django static..."
rm -rf "$STATIC/_next"
cp -r "$LANDING/out/_next" "$STATIC/_next"

mkdir -p "$STATIC/landing"
cp "$LANDING/out/index.html" "$STATIC/landing/index.html"

for f in "$LANDING/out"/*.png "$LANDING/out"/*.ico "$LANDING/out"/*.svg; do
  [ -f "$f" ] && cp "$f" "$STATIC/landing/"
done

# Fix image paths: Next.js exports /img.png but Django serves at /static/landing/img.png
sed -i 's|src="/\([^_][^"]*\.png\)"|src="/static/landing/\1"|g' "$STATIC/landing/index.html"
sed -i 's|src="/\([^_][^"]*\.svg\)"|src="/static/landing/\1"|g' "$STATIC/landing/index.html"
sed -i 's|src="/\([^_][^"]*\.ico\)"|src="/static/landing/\1"|g' "$STATIC/landing/index.html"

echo "✓ Landing page built and deployed to static/"
