'use client';

import React, { useState, useEffect, useCallback, useRef } from 'react';
import GameBoard from '@/components/GameBoard';
import AgentSummaryModal from '@/components/AgentSummaryModal';
import GameApi from '@/lib/gameApi';
import { Card, GameUIState, Rank } from '@/types/game';

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
  const [dragStart, setDragStart] = useState<{ x: number; y: number } | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  // Auto-pan to current player
  const [previousCurrentPlayer, setPreviousCurrentPlayer] = useState<string | null>(null);

  // Modal state
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [selectedPlayerId, setSelectedPlayerId] = useState<string | null>(null);
  const [selectedPlayerSummary, setSelectedPlayerSummary] = useState<any>(null);
  const [isLoadingSummary, setIsLoadingSummary] = useState(false);

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

  // Handle player card clicks
  const handlePlayerCardClick = useCallback(async (playerId: string) => {
    if (isLoadingSummary) return;
    
    setIsLoadingSummary(true);
    setSelectedPlayerId(playerId);
    
    try {
      const response = await gameApi.getAgentSummary(playerId);
      // Always open modal regardless of success - modal handles empty summaries
      setSelectedPlayerSummary(response.success ? response.data : null);
      setIsModalOpen(true);
      
      // Only set error if there was an actual error, not just "no summary available"
      if (!response.success && response.error && !response.error.includes('No summary available')) {
        setError(response.error);
      } else {
        setError(null); // Clear any previous errors
      }
    } catch (err) {
      setError('Failed to get agent summary');
      // Still open modal to show the error
      setSelectedPlayerSummary(null);
      setIsModalOpen(true);
    } finally {
      setIsLoadingSummary(false);
    }
  }, [gameApi, isLoadingSummary]);

  // Handle modal close
  const handleModalClose = useCallback(() => {
    setIsModalOpen(false);
    setSelectedPlayerId(null);
    setSelectedPlayerSummary(null);
  }, []);

  // Handle game events for animations
  const handleGameEvent = useCallback((event: any) => {
    console.log('📨 Game event received:', event.type, event.timestamp);
    setLastGameEvent(event);
    
    // Handle different event types
    if (event.type === 'game_action') {
      const action = event.action;
      console.log('Action:', action);
      
      // Handle turn_start events to immediately update current player
      if (action.type === 'turn_start') {
        const currentPlayerId = action.data.player_id;
        console.log('Turn start for player:', currentPlayerId);
        
        // Convert rank name to Rank enum
        const convertRank = (rankName: string): Rank => {
          const rankMap: Record<string, Rank> = {
            'Ace': Rank.ACE,
            '2': Rank.TWO,
            '3': Rank.THREE,
            '4': Rank.FOUR,
            '5': Rank.FIVE,
            '6': Rank.SIX,
            '7': Rank.SEVEN,
            '8': Rank.EIGHT,
            '9': Rank.NINE,
            '10': Rank.TEN,
            'Jack': Rank.JACK,
            'Queen': Rank.QUEEN,
            'King': Rank.KING
          };
          return rankMap[rankName] || Rank.ACE;
        };
        
        // Immediately update the current player in the game state
        setGameState(prevState => {
          if (!prevState) return prevState;
          
          const updatedPlayers = prevState.players.map(player => ({
            ...player,
            is_current_player: player.id === currentPlayerId
          }));
          
          return {
            ...prevState,
            players: updatedPlayers,
            turn_number: action.data.turn_number,
            current_expected_rank: convertRank(action.data.expected_rank)
          };
        });
        
        // Still refresh game state but don't wait for it
        refreshGameState();
      } else if (action.type === 'card_play') {
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
      // Check if click is on a player card or its children
      const target = e.target as HTMLElement;
      const isPlayerCard = target.closest('[data-player-card]');
      
      if (!isPlayerCard) {
        // Don't immediately set dragging - wait for movement
        setDragStart({ x: e.clientX - pan.x, y: e.clientY - pan.y });
      }
    }
  }, [pan]);

  const handleMouseMove = useCallback((e: React.MouseEvent) => {
    // Only handle mouse movement if we have a drag start point
    if (dragStart) {
      if (!isDragging) {
        // Check if we've moved enough to start dragging
        const deltaX = Math.abs(e.clientX - (dragStart.x + pan.x));
        const deltaY = Math.abs(e.clientY - (dragStart.y + pan.y));
        
        if (deltaX > 5 || deltaY > 5) { // 5px threshold
          setIsDragging(true);
        }
      }
      
      if (isDragging) {
        setPan({
          x: e.clientX - dragStart.x,
          y: e.clientY - dragStart.y
        });
      }
    }
  }, [isDragging, dragStart, pan]);

  const handleMouseUp = useCallback(() => {
    setIsDragging(false);
    setDragStart(null);
  }, []);

  // Function to calculate player position (matching GameBoard logic)
  const getPlayerPosition = useCallback((index: number, total: number) => {
    const centerX = typeof window !== 'undefined' ? window.innerWidth / 2 : 800;
    const centerY = typeof window !== 'undefined' ? window.innerHeight / 2 : 400;
    
    // Use different radii for horizontal and vertical axes to form an ellipse
    const horizontalRadius = (typeof window !== 'undefined' ? window.innerWidth / 2 : 600) * 0.8;
    const verticalRadius = (typeof window !== 'undefined' ? window.innerHeight / 2 : 400) * 0.7;
    
    const angle = (index * 2 * Math.PI) / total - Math.PI / 2;
    
    return {
      x: centerX + Math.cos(angle) * horizontalRadius,
      y: centerY + Math.sin(angle) * verticalRadius
    };
  }, []);

  // Function to calculate pan offset to center a specific player
  const getPanToPlayer = useCallback((playerId: string) => {
    if (!gameState) return { x: 0, y: 0 };
    
    const playerIndex = gameState.players.findIndex(p => p.id === playerId);
    if (playerIndex === -1) return { x: 0, y: 0 };
    
    const playerPosition = getPlayerPosition(playerIndex, gameState.players.length);
    const screenCenter = {
      x: typeof window !== 'undefined' ? window.innerWidth / 2 : 800,
      y: typeof window !== 'undefined' ? window.innerHeight / 2 : 400
    };
    
    // Calculate the offset needed to center the player on screen
    return {
      x: screenCenter.x - playerPosition.x,
      y: screenCenter.y - playerPosition.y
    };
  }, [gameState, getPlayerPosition]);

  // Auto-pan to current player when their turn starts
  useEffect(() => {
    if (!gameState || isDragging) return;
    
    const currentPlayer = gameState.players.find(p => p.is_current_player);
    if (currentPlayer && currentPlayer.id !== previousCurrentPlayer) {
      const newPan = getPanToPlayer(currentPlayer.id);
      
      // Smooth transition animation
      const animationDuration = 800;
      const startTime = Date.now();
      const startPan = { ...pan };
      
      const animateToPlayer = () => {
        const elapsed = Date.now() - startTime;
        const progress = Math.min(elapsed / animationDuration, 1);
        
        // Easing function for smooth animation
        const easeProgress = 1 - Math.pow(1 - progress, 3);
        
        const currentPan = {
          x: startPan.x + (newPan.x - startPan.x) * easeProgress,
          y: startPan.y + (newPan.y - startPan.y) * easeProgress
        };
        
        setPan(currentPan);
        
        if (progress < 1) {
          requestAnimationFrame(animateToPlayer);
        }
      };
      
      requestAnimationFrame(animateToPlayer);
      setPreviousCurrentPlayer(currentPlayer.id);
    }
  }, [gameState, isDragging, previousCurrentPlayer, getPanToPlayer, pan]);

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
          onPlayerCardClick={handlePlayerCardClick}
        />
      </div>

      <AgentSummaryModal
        isOpen={isModalOpen}
        onClose={handleModalClose}
        playerId={selectedPlayerId}
        summary={selectedPlayerSummary}
        isLoading={isLoadingSummary}
        error={error}
      />
    </div>
  );
}
