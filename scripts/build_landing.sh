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
# _next/ assets → served by whitenoise at /static/_next/
rm -rf "$STATIC/_next"
cp -r "$LANDING/out/_next" "$STATIC/_next"

# index.html → Django root view reads this file
mkdir -p "$STATIC/landing"
cp "$LANDING/out/index.html" "$STATIC/landing/index.html"

# Copy any other static assets (images etc.)
for f in "$LANDING/out"/*.png "$LANDING/out"/*.ico "$LANDING/out"/*.svg; do
  [ -f "$f" ] && cp "$f" "$STATIC/landing/"
done

echo "✓ Landing page built and deployed to static/"
