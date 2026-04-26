#!/bin/bash
# Quick start script for the Advanced Context-Aware RAG

echo "🚀 Advanced Context-Aware RAG - Quick Start"
echo "=============================================="
echo ""

# Check Python
echo "📋 Checking Python..."
python_version=$(python --version 2>&1)
echo "   ✓ $python_version"

# Check Node
echo "📋 Checking Node.js..."
node_version=$(node --version 2>&1)
echo "   ✓ Node.js $node_version"

# Backend setup
echo ""
echo "📦 Setting up Backend..."
cd backend

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "   Creating virtual environment..."
    python -m venv venv
fi

# Activate virtual environment
echo "   Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "   Installing Python dependencies..."
pip install -q -r requirements.txt

echo "   ✓ Backend setup complete"

# Frontend setup
echo ""
echo "📦 Setting up Frontend..."
cd ../frontend

# Install dependencies
if [ ! -d "node_modules" ]; then
    echo "   Installing Node dependencies..."
    npm install -q
fi

echo "   ✓ Frontend setup complete"

echo ""
echo "✅ Setup Complete!"
echo ""
echo "🎯 Next Steps:"
echo "   1. Terminal 1 - Start Backend:"
echo "      cd backend && source venv/bin/activate && python app.py"
echo ""
echo "   2. Terminal 2 - Start Frontend:"
echo "      cd frontend && npm start"
echo ""
echo "   3. Open browser:"
echo "      http://localhost:3000"
echo ""
echo "🚀 Happy RAG-ing!"
