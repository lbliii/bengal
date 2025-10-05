#!/bin/bash
# Quick test script for dev server incremental builds
# Usage: ./tests/manual/quick_test_dev_server.sh

set -e

cd "$(dirname "$0")/../../examples/showcase"

echo "🧪 Testing Dev Server Incremental Builds"
echo "=========================================="
echo ""

# Clean build
echo "1️⃣  Cleaning..."
bengal clean -f > /dev/null 2>&1

# Initial build (baseline)
echo "2️⃣  Initial build..."
time bengal build --quiet

# Wait a moment
sleep 1

# Test single file change with incremental
echo ""
echo "3️⃣  Testing incremental build (1 file change)..."
echo "   Modifying content/index.md..."
echo "# Test change at $(date +%H:%M:%S)" >> content/index.md

echo "   Running incremental build..."
time bengal build --incremental --quiet

# Restore
git restore content/index.md

echo ""
echo "✅ Test complete!"
echo ""
echo "Expected results:"
echo "  - Initial build:      ~1.2s (full build)"
echo "  - Incremental build:  < 0.3s (5x faster!)"
echo ""
echo "If incremental build was significantly faster, the optimization is working! 🚀"

