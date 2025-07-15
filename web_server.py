#!/usr/bin/env python3
"""
Web server for BS Card Game
Serves the game state via REST API and WebSocket for real-time updates
"""

import asyncio
import json
import threading
import time
from typing import Dict, List, Any, Optional
from datetime import datetime
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from utils.game_orchestrator import GameOrchestrator
from utils.game_logger import LogLevel
from utils.card_system import Card, Rank, Suit
from characters import alice, marcus, randall, susan

app = FastAPI(title="BS Card Game API", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global game state
game_orchestrator: Optional[GameOrchestrator] = None
game_thread: Optional[threading.Thread] = None
game_events: List[Dict[str, Any]] = []
connected_clients: List[WebSocket] = []
game_running = False

class GameStateResponse(BaseModel):
    game_state: Dict[str, Any]
    player_hands: Dict[str, List[Dict[str, Any]]]
    center_pile: List[Dict[str, Any]]

def card_to_dict(card: Card) -> Dict[str, Any]:
    """Convert a Card object to a dictionary"""
    return {
        "suit": card.suit.value,
        "rank": card.rank.value,
        "id": f"{card.suit.value}_{card.rank.value}"
    }

def action_callback(action_data: Dict[str, Any]):
    """Callback function for game actions"""
    print(f"📡 DEBUG: Action callback received: {action_data}")
    
    # Special debug logging for BS calls
    if action_data.get("type") == "bs_call":
        print(f"📡 DEBUG: BS call action data: {action_data}")
        print(f"📡 DEBUG: BS call reasoning: '{action_data.get('data', {}).get('reasoning', '')}'")
    
    # Create event for frontend
    event = {
        "type": "game_action",
        "action": action_data,
        "timestamp": datetime.now().isoformat()
    }
    
    # Add to event queue
    game_events.append(event)
    
    # Try to broadcast to websockets
    try:
        loop = asyncio.get_event_loop()
        loop.create_task(broadcast_event(event))
    except RuntimeError:
        # No event loop in this thread, that's okay
        pass

def create_player_configs() -> List[Dict[str, str]]:
    """Create player configurations with character personalities"""
    return [
        {
            "id": "alice",
            "personality": alice.personality,
            "play_style": alice.talking_style + "\n\n" + alice.play_style
        },
        {
            "id": "marcus", 
            "personality": marcus.personality,
            "play_style": marcus.talking_style + "\n\n" + marcus.play_style
        },
        {
            "id": "randall",
            "personality": randall.personality,
            "play_style": randall.talking_style + "\n\n" + randall.play_style
        },
        {
            "id": "susan",
            "personality": susan.personality,
            "play_style": susan.talking_style + "\n\n" + susan.play_style
        }
    ]

def get_game_state_dict() -> Dict[str, Any]:
    """Get current game state as dictionary"""
    if not game_orchestrator:
        return {}
    
    game_info = game_orchestrator.get_game_state_info()
    
    # Convert to frontend format
    players = []
    for player_id in game_orchestrator.player_ids:
        hand_counts = game_info.get("hand_counts", {})
        players.append({
            "id": player_id,
            "name": player_id.title(),
            "hand_count": hand_counts.get(player_id, 0),
            "is_current_player": player_id == game_info.get("current_player")
        })
    
    return {
        "players": players,
        "current_expected_rank": game_info.get("expected_rank", "Ace"),
        "center_pile_count": game_info.get("center_pile_count", 0),
        "turn_number": game_info.get("turn_number", 1),
        "last_action": game_orchestrator.game_state.game_state.last_action or "Game starting...",
        "game_phase": game_info.get("game_phase", "playing"),
        "winner": game_info.get("winner")
    }

def get_player_hands_dict() -> Dict[str, List[Dict[str, Any]]]:
    """Get all player hands as dictionary"""
    if not game_orchestrator:
        return {}
    
    hands = {}
    for player_id in game_orchestrator.player_ids:
        player_cards = game_orchestrator.game_state.game_state.player_hands.get(player_id, [])
        hands[player_id] = [card_to_dict(card) for card in player_cards]
    
    return hands

def get_center_pile_dict() -> List[Dict[str, Any]]:
    """Get center pile as list of card dictionaries"""
    if not game_orchestrator:
        return []
    
    center_cards = []
    for played_cards in game_orchestrator.game_state.game_state.center_pile:
        center_cards.extend([card_to_dict(card) for card in played_cards.cards])
    
    return center_cards

async def broadcast_event(event: Dict[str, Any]):
    """Broadcast event to all connected WebSocket clients"""
    # Remove clients that are disconnected
    disconnected_clients = []
    for client in connected_clients:
        try:
            await client.send_text(json.dumps(event))
        except:
            disconnected_clients.append(client)
    
    for client in disconnected_clients:
        connected_clients.remove(client)

def run_game_loop():
    """Run the game loop in a separate thread"""
    global game_orchestrator, game_running
    
    if not game_orchestrator:
        return
    
    game_running = True
    
    try:
        print("Starting game loop...")
        
        # Run the game
        results = game_orchestrator.run_game()
        
        print(f"Game ended: {results}")
        
        # Add game end event
        end_event = {
            "type": "game_end",
            "winner": results.get("winner"),
            "turn_count": results.get("turn_count"),
            "timestamp": datetime.now().isoformat()
        }
        game_events.append(end_event)
        
    except Exception as e:
        print(f"Error in game loop: {e}")
        import traceback
        traceback.print_exc()
    finally:
        game_running = False

@app.post("/start_game")
async def start_game():
    """Start a new game"""
    global game_orchestrator, game_thread, game_running
    
    if game_running:
        return {"success": False, "message": "Game already running"}
    
    try:
        # Create player configurations
        player_configs = create_player_configs()
        
        # Create game orchestrator with action callback
        game_orchestrator = GameOrchestrator(
            player_configs, 
            LogLevel.DEBUG, 
            action_callback=action_callback
        )
        
        # Start game in separate thread
        game_thread = threading.Thread(target=run_game_loop)
        game_thread.daemon = True
        game_thread.start()
        
        # Broadcast game start event
        start_event = {
            "type": "game_start",
            "players": [config["id"] for config in player_configs],
            "timestamp": datetime.now().isoformat()
        }
        game_events.append(start_event)
        await broadcast_event(start_event)
        
        return {"success": True, "message": "Game started"}
        
    except Exception as e:
        return {"success": False, "message": str(e)}

@app.get("/game_state")
async def get_game_state():
    """Get current game state"""
    if not game_orchestrator:
        # Return empty game state instead of 404
        return GameStateResponse(
            game_state={
                "players": [],
                "current_expected_rank": "Ace",
                "center_pile_count": 0,
                "turn_number": 0,
                "last_action": "No game active",
                "game_phase": "waiting",
                "winner": None
            },
            player_hands={},
            center_pile=[]
        )
    
    return GameStateResponse(
        game_state=get_game_state_dict(),
        player_hands=get_player_hands_dict(),
        center_pile=get_center_pile_dict()
    )

@app.post("/advance_turn")
async def advance_turn():
    """Advance to next turn (for debugging)"""
    if not game_orchestrator:
        raise HTTPException(status_code=404, detail="No active game")
    
    try:
        # This is mainly for debugging - the game should advance automatically
        await broadcast_event({
            "type": "turn_advance",
            "turn_number": game_orchestrator.game_state.game_state.turn_number,
            "timestamp": datetime.now().isoformat()
        })
        
        return {"success": True, "message": "Turn advanced"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/game_events")
async def get_game_events():
    """Server-Sent Events endpoint for real-time updates"""
    async def event_generator():
        while True:
            if game_events:
                event = game_events.pop(0)
                yield f"data: {json.dumps(event)}\n\n"
            await asyncio.sleep(0.1)
    
    return StreamingResponse(
        event_generator(), 
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time game updates"""
    await websocket.accept()
    connected_clients.append(websocket)
    
    try:
        while True:
            # Send current game state periodically
            if game_orchestrator:
                game_state = {
                    "type": "game_state_update",
                    "game_state": get_game_state_dict(),
                    "player_hands": get_player_hands_dict(),
                    "center_pile": get_center_pile_dict(),
                    "timestamp": datetime.now().isoformat()
                }
                await websocket.send_text(json.dumps(game_state))
            
            await asyncio.sleep(2)  # Send updates every 2 seconds
            
    except WebSocketDisconnect:
        connected_clients.remove(websocket)

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy", 
        "timestamp": datetime.now().isoformat(),
        "game_running": game_running,
        "connected_clients": len(connected_clients)
    }

if __name__ == "__main__":
    import uvicorn
    print("Starting BS Card Game Web Server...")
    print("Frontend should connect to: http://localhost:8000")
    print("API docs available at: http://localhost:8000/docs")
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=False) 