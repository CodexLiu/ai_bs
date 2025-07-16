# BS Card Game

A web-based BS (Bullshit) card game with AI players.

## Quick Start

### 1. Install Python dependencies
```bash
pip install -r requirements.txt
```

### 2. Set up environment variables
Create a `.env.local` file with:
```
OPENAI_API_KEY=your_openai_key_here
GOOGLE_GEMINI_API_KEY=your_gemini_key_here
```

### 3. Run the backend server
```bash
python web_server.py
```
The API will be available at http://localhost:8000

### 4. Run the frontend
```bash
cd bs-game-frontend
npm install
npm run dev
```
The frontend will be available at http://localhost:3000

## That's it!

The frontend will connect to the backend API automatically. Start a game from the web interface and watch AI players compete! 