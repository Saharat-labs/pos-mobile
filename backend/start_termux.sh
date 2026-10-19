#!/data/data/com.termux/files/usr/bin/bash
# POS-MOBILE Backend - Termux Startup Script

set -e

BACKEND_DIR="/data/data/com.termux/files/home/projects/pos-mobile/backend"
VENV_DIR="$BACKEND_DIR/venv"

echo "🚀 POS-MOBILE Backend - Termux Startup"
echo "======================================"

# Check if we're in Termux
if [ ! -d "/data/data/com.termux" ]; then
    echo "⚠️  Not running in Termux, but continuing anyway..."
fi

# Navigate to backend directory
cd "$BACKEND_DIR" || {
    echo "❌ Backend directory not found: $BACKEND_DIR"
    exit 1
}

# Create virtual environment if not exists
if [ ! -d "$VENV_DIR" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv "$VENV_DIR"
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source "$VENV_DIR/bin/activate"

# Upgrade pip
pip install --upgrade pip -q

# Install dependencies
echo "📦 Installing dependencies..."
pip install -r requirements.txt -q

# Check for .env
if [ ! -f ".env" ]; then
    echo "⚙️  Creating .env from example..."
    cp .env.example .env
fi

# Run database migrations (create tables)
echo "🗄️  Initializing database..."
python -c "
import asyncio
from app.database import init_db
asyncio.run(init_db())
print('✅ Database initialized')
"

# Start server
echo "🌐 Starting server on http://0.0.0.0:8000"
echo "📖 API docs: http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop"
echo ""

exec python run.py