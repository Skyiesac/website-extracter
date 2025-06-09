#!/bin/bash

echo "🚀 Starting Website Cloner..."

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 is not installed. Please install Python3 first."
    exit 1
fi

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    echo "❌ Node.js is not installed. Please install Node.js first."
    exit 1
fi

# Start Backend
echo "🔧 Starting Backend..."
cd backend

# Check if virtual environment exists, create if not
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install dependencies
echo "📦 Installing Python dependencies..."
pip install -r requirements.txt

# Install Playwright browsers if not already installed
echo "🌐 Installing Playwright browsers..."
playwright install chromium

# Start the FastAPI server
echo "🚀 Starting FastAPI server..."
uvicorn hello:app --reload --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!
cd ..

# Wait a moment for backend to start
sleep 3

# Start Frontend
echo "🎨 Starting Frontend..."
cd frontend

# Clear cache and install dependencies
echo "📦 Installing Node.js dependencies..."
rm -rf .next
npm install

# Start the Next.js development server
echo "🚀 Starting Next.js development server..."
npm run dev &
FRONTEND_PID=$!
cd ..

echo "✅ All services started!"
echo "📱 Frontend: http://localhost:3000"
echo "🔌 Backend: http://localhost:8000"
echo "📚 API Docs: http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop all services"

# Wait for interrupt
trap "echo '🛑 Stopping services...'; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; echo '✅ All services stopped'; exit" INT

wait 