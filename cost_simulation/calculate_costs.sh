#!/bin/bash

# Cost Calculator Script
# Quick way to calculate costs for your volume

echo "╔════════════════════════════════════════════════════════════╗"
echo "║        NEWS CLASSIFICATION - COST CALCULATOR               ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Error: Python 3 not found"
    exit 1
fi

# Run calculations for different volumes
echo "📊 Calculating costs for different daily volumes..."
echo ""

echo "─────────────────────────────────────────────────────────────"
echo "Volume: 10,000 URLs/day"
echo "─────────────────────────────────────────────────────────────"
python3 cost_calculator.py --urls 10000

echo ""
echo "─────────────────────────────────────────────────────────────"
echo "Volume: 12,000 URLs/day"
echo "─────────────────────────────────────────────────────────────"
python3 cost_calculator.py --urls 12000

echo ""
echo "📝 Custom calculation:"
echo "   Run: python3 cost_calculator.py --urls YOUR_VOLUME"
echo ""
