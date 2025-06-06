# Orchids SWE Intern Challenge 
This project consists of a backend built with FastAPI and a frontend built with Next.js and TypeScript.

## 📋 Prerequisites

Before you begin, ensure you have the following installed:
- Python 3.11.8 
- Node.js 18 or higher(for Next.js)
- npm (comes with Node.js)
- Google Gemini API key (for AI-powered cloning)

## 🚀 Installation Guide

### 1. Clone the Repository
```bash
cd orchids-challenge
```

### 2. Backend Setup

The backend uses `uv` for package management.

#### Installation
```bash
cd backend
uv sync
```

#### Environment Setup
Create a `.env` file in the backend directory:
```bash
GOOGLE_API_KEY=your_gemini_api_key
```

### 3. Frontend Setup

The frontend is built with Next.js and TypeScript.

#### Installation
```bash
cd frontend
npm install
```


## 🏃‍♂️ Running the Application

### Backend

To run the backend development server, use the following command:

```bash
cd backend
uv run fastapi dev
```

The backend will be available at `http://localhost:8000`

### Frontend

To start the frontend development server, run:

```bash
cd frontend
npm run dev
```

The frontend will be available at `http://localhost:3000`

## 🔧 Troubleshooting

If you encounter any issues:

1. **Backend Issues**
   - Ensure Python 3.11.8 is installed(Use pyenv)
   - Check if `uv` is properly installed
   - Verify your Google API key is valid

2. **Frontend Issues**
   - Clear npm cache: `npm cache clean --force`
   - Delete node_modules and reinstall: 
     ```bash
     rm -rf node_modules
     npm install
     ```
   - Ensure all environment variables are set correctly
