'use client';

import React, { useState, useEffect, useCallback, useRef } from 'react';
import GameBoard from '@/components/GameBoard';
import GameApi from '@/lib/gameApi';
import { Card, GameUIState } from '@/types/game';

export default function GamePage() {
  const [gameState, setGameState] = useState<GameUIState | null>(null);
  const [playerHands, setPlayerHands] = useState<Record<string, Card[]>>({});
  const [centerPile, setCenterPile] = useState<Card[]>([]);
  const [gameApi] = useState(new GameApi());
  const [isConnected, setIsConnected] = useState(false);
  const [isGameStarted, setIsGameStarted] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isStarting, setIsStarting] = useState(false);
  
  // Animation state
  const [lastGameEvent, setLastGameEvent] = useState<any>(null);
  const [animatingCards, setAnimatingCards] = useState<string[]>([]);

  // Pan and zoom state
  const [zoom, setZoom] = useState(1.0);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [isDragging, setIsDragging] = useState(false);
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });
  const containerRef = useRef<HTMLDivElement>(null);

  // Function to refresh game state
  const refreshGameState = useCallback(async () => {
    try {
      const response = await gameApi.getGameState();
      if (response.success) {
        setGameState(response.data.gameState);
        setPlayerHands(response.data.playerHands);
        setCenterPile(response.data.centerPile);
        setIsConnected(true);
        setIsGameStarted(true);
        setError(null);
        return true;
      } else {
        setError(response.error || 'Failed to get game state');
        return false;
      }
    } catch (err) {
      setError('Failed to connect to backend');
      setIsConnected(false);
      return false;
    }
  }, [gameApi]);

  // Handle game events for animations
  const handleGameEvent = useCallback((event: any) => {
    console.log('📨 Game event received:', event.type, event.timestamp);
    setLastGameEvent(event);
    
    // Handle different event types
    if (event.type === 'game_action') {
      const action = event.action;
      console.log('Action:', action);
      
      if (action.type === 'card_play') {
        // Set animating cards for smooth transitions
        const playedCards = action.data.actual_cards || [];
        console.log('Played cards:', playedCards);
        
        // Convert backend card format to frontend format
        const animatingCardIds = playedCards.map((card: any) => {
          // Backend sends rank as number, suit as string
          const cardId = `${card.suit}_${card.rank}`;
          console.log('Generated card ID:', cardId);
          return cardId;
        });
        
        console.log('Setting animating cards:', animatingCardIds);
        setAnimatingCards(animatingCardIds);
        
        // Clear animating cards after animation completes
        setTimeout(() => {
          setAnimatingCards([]);
        }, 1000);
        
        // Delay state refresh to allow animation setup
        setTimeout(() => {
          refreshGameState();
        }, 100);
      } else {
        // For non-animation events, refresh immediately
        refreshGameState();
      }
    } else {
      // For non-game-action events, refresh immediately
      refreshGameState();
    }
  }, [refreshGameState]);

  useEffect(() => {
    // Try to connect to the backend and check for existing game
    const connectToBackend = async () => {
      const success = await refreshGameState();
      if (!success) {
        setIsConnected(false);
        setError('Backend not available');
      }
    };

    connectToBackend();

    // Subscribe to game events
    gameApi.subscribeToGameEvents(handleGameEvent);

    // Cleanup on unmount
    return () => {
      gameApi.disconnect();
    };
  }, [gameApi, handleGameEvent]);

  const handleStartGame = async () => {
    if (isStarting) return;
    
    setIsStarting(true);
    setError(null);
    
    try {
      const response = await gameApi.startGame();
      if (response.success) {
        setIsConnected(true);
        // Refresh game state after starting
        await refreshGameState();
      } else {
        setError(response.error || 'Failed to start game');
      }
    } catch (err) {
      setError('Failed to start game');
      setIsConnected(false);
    } finally {
      setIsStarting(false);
    }
  };

  // Pan and zoom handlers
  const handleWheel = useCallback((e: React.WheelEvent) => {
    e.preventDefault();
    const delta = e.deltaY > 0 ? 0.9 : 1.1;
    setZoom(prev => Math.max(0.5, Math.min(2, prev * delta)));
  }, []);

  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    if (e.button === 0) { // Left click
      setIsDragging(true);
      setDragStart({ x: e.clientX - pan.x, y: e.clientY - pan.y });
    }
  }, [pan]);

  const handleMouseMove = useCallback((e: React.MouseEvent) => {
    if (isDragging) {
      setPan({
        x: e.clientX - dragStart.x,
        y: e.clientY - dragStart.y
      });
    }
  }, [isDragging, dragStart]);

  const handleMouseUp = useCallback(() => {
    setIsDragging(false);
  }, []);

  // Show start game screen if no game is active
  if (!isGameStarted || !gameState || gameState.game_phase === 'waiting' || gameState.last_action === 'No game active') {
    return (
      <div className="min-h-screen bg-gradient-to-br from-green-800 to-green-900 flex items-center justify-center">
        <div className="text-center">
          <h1 className="text-6xl font-bold text-white mb-8">BS Agents</h1>          
          <button
            onClick={handleStartGame}
            disabled={isStarting}
            className={`px-12 py-6 text-2xl font-bold rounded-lg transition-all ${
              isStarting 
                ? 'bg-gray-600 text-gray-300 cursor-not-allowed' 
                : 'bg-blue-600 hover:bg-blue-700 text-white hover:scale-105'
            }`}
          >
            {isStarting ? '🎲 Starting Game...' : 'Start'}
          </button>
          
          {error && (
            <div className="mt-6 px-6 py-4 bg-red-600 text-white rounded-lg max-w-md mx-auto">
              {error}
            </div>
          )}
          
          {!isConnected && (
            <div className="mt-4 px-6 py-3 bg-yellow-600 text-white rounded-lg max-w-md mx-auto">
              🔌 Connecting to backend...
            </div>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-100">
      {/* Game board container with zoom and pan */}
      <div 
        ref={containerRef}
        className="relative w-full h-screen overflow-hidden"
        style={{ cursor: isDragging ? 'grabbing' : 'grab' }}
        onWheel={handleWheel}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseUp}
      >
        <GameBoard
          gameState={gameState}
          playerHands={playerHands}
          centerPile={centerPile}
          zoom={zoom}
          pan={pan}
          lastGameEvent={lastGameEvent}
          animatingCards={animatingCards}
          onCardPlay={(playerId, cardIds) => {
            console.log(`Player ${playerId} played cards:`, cardIds);
          }}
        />
      </div>
    </div>
  );
}
