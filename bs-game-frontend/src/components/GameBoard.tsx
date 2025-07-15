import React, { useState, useEffect, useRef, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import Card from './Card';
import ThoughtBubble from './ThoughtBubble';
import { Card as CardType, GameUIState, PlayerInfo, Rank } from '@/types/game';

interface GameBoardProps {
  gameState: GameUIState;
  playerHands: Record<string, CardType[]>;
  centerPile: CardType[];
  onCardPlay?: (playerId: string, cardIds: string[]) => void;
  zoom?: number;
  pan?: { x: number; y: number };
  lastGameEvent?: any;
  animatingCards?: string[];
}

const GameBoard: React.FC<GameBoardProps> = ({ 
  gameState, 
  playerHands, 
  centerPile,
  onCardPlay,
  zoom = 1,
  pan = { x: 0, y: 0 },
  lastGameEvent,
  animatingCards = []
}) => {
  const [lastAction, setLastAction] = useState<string>('');
  const [newlyAddedCards, setNewlyAddedCards] = useState<Set<string>>(new Set());
  const [animatingToCenter, setAnimatingToCenter] = useState<Map<string, { from: any, to: any }>>(new Map());
  const [animatingFromCenter, setAnimatingFromCenter] = useState<Map<string, { from: any, to: any }>>(new Map());
  const [activeThoughts, setActiveThoughts] = useState<Map<string, { reasoning: string, timestamp: number }>>(new Map());
  const [animatingThoughts, setAnimatingThoughts] = useState<Set<string>>(new Set());
  const processedEventsRef = useRef<Set<string>>(new Set());

  // Terminal animation states
  const [displayTurn, setDisplayTurn] = useState<string>('');
  const [displayRank, setDisplayRank] = useState<string>('');
  const [isTyping, setIsTyping] = useState<boolean>(false);
  const previousTurnRef = useRef<number>(0);
  const previousRankRef = useRef<Rank | null>(null);

  // Update last action with more detailed message
  useEffect(() => {
    if (gameState.last_action) {
      setLastAction(gameState.last_action);
    }
  }, [gameState.last_action]);

  // Terminal typing animation effect
  useEffect(() => {
    const currentTurn = gameState.turn_number;
    const currentRank = gameState.current_expected_rank;
    
    const targetTurnText = `Turn ${currentTurn}`;
    const targetRankText = getRankName(currentRank);

    // Check if values have changed
    if (currentTurn !== previousTurnRef.current || currentRank !== previousRankRef.current) {
      setIsTyping(true);
      
      // Step 1: Backspace animation (clear existing text)
      const backspaceInterval = setInterval(() => {
        setDisplayTurn(prev => prev.slice(0, -1));
        setDisplayRank(prev => prev.slice(0, -1));
      }, 50);

      setTimeout(() => {
        clearInterval(backspaceInterval);
        setDisplayTurn('');
        setDisplayRank('');
        
        // Step 2: Typing animation (add new text)
        let turnIndex = 0;
        let rankIndex = 0;
        
        const typingInterval = setInterval(() => {
          if (turnIndex < targetTurnText.length) {
            setDisplayTurn(targetTurnText.slice(0, turnIndex + 1));
            turnIndex++;
          }
          if (rankIndex < targetRankText.length) {
            setDisplayRank(targetRankText.slice(0, rankIndex + 1));
            rankIndex++;
          }
          
          if (turnIndex >= targetTurnText.length && rankIndex >= targetRankText.length) {
            clearInterval(typingInterval);
            setIsTyping(false);
          }
        }, 80);
      }, Math.max(displayTurn.length, displayRank.length) * 50 + 200);
      
      previousTurnRef.current = currentTurn;
      previousRankRef.current = currentRank;
    } else if (displayTurn === '' && displayRank === '') {
      // Initialize on first load
      setDisplayTurn(targetTurnText);
      setDisplayRank(targetRankText);
      previousTurnRef.current = currentTurn;
      previousRankRef.current = currentRank;
    }
  }, [gameState.turn_number, gameState.current_expected_rank]);

  // Handle animation events from backend
  useEffect(() => {
    if (lastGameEvent?.type === 'game_action') {
      const action = lastGameEvent.action;
      const playerId = action.data?.player_id || action.data?.caller;
      const reasoning = action.data?.reasoning || '';
      const eventId = `${lastGameEvent.timestamp}-${action.type}-${playerId}-${reasoning.slice(0, 50)}`;
      
      // Atomic duplicate prevention - check and add in one operation
      const currentSize = processedEventsRef.current.size;
      processedEventsRef.current.add(eventId);
      
      // If size didn't change, this eventId was already in the set (duplicate)
      if (processedEventsRef.current.size === currentSize) {
        console.log('⏭️ Skipping duplicate event:', eventId);
        return;
      }
      
      // Clean up old event IDs to prevent memory leaks (keep last 50)
      if (processedEventsRef.current.size > 50) {
        const eventsArray = Array.from(processedEventsRef.current);
        processedEventsRef.current = new Set(eventsArray.slice(-25));
      }
      
      console.log('Processing game action for animation:', action);
      
      if (action.type === 'card_play') {
        // Create animations for cards moving to center pile
        const actualCards = action.data.actual_cards || [];
        
        console.log('Setting up card play animation for:', playerId, actualCards);
        
        // Find player position
        const playerIndex = gameState.players.findIndex(p => p.id === playerId);
        const playerPos = getPlayerPosition(playerIndex, gameState.players.length);
        const centerContainerPos = getCenterContainerPosition();
        
        const newAnimations = new Map();
        
        actualCards.forEach((backendCard: any, index: number) => {
          // Create card ID in the same format as frontend
          const cardId = `${backendCard.suit}_${backendCard.rank}`;
          console.log('Setting up animation for card:', cardId);
          
          // Calculate final position within center pile (relative to center container)
          const finalPilePos = getCenterPilePosition(index);
          
          newAnimations.set(cardId, {
            from: { 
              x: playerPos.x - centerContainerPos.x, 
              y: playerPos.y - centerContainerPos.y 
            },
            to: { 
              x: finalPilePos.x, 
              y: finalPilePos.y 
            }
          });
        });
        
        setAnimatingToCenter(newAnimations);
        
        // Mark cards as newly added for detection
        const newCardIds = actualCards.map((card: any) => `${card.suit}_${card.rank}`);
        setNewlyAddedCards(new Set(newCardIds));
        
        // Clear animations after they complete
        setTimeout(() => {
          setAnimatingToCenter(new Map());
          setNewlyAddedCards(new Set());
        }, 1000);
      }
      
      if (action.type === 'bs_call') {
        // Handle BS call animations - cards moving from center to player
        const wasBS = action.data.was_bs;
        const targetPlayerId = wasBS ? action.data.target : action.data.caller;
        
        console.log('Setting up BS call animation for:', targetPlayerId, 'was_bs:', wasBS);
        
        const targetPlayerIndex = gameState.players.findIndex(p => p.id === targetPlayerId);
        const targetPlayerPos = getPlayerPosition(targetPlayerIndex, gameState.players.length);
        const centerContainerPos = getCenterContainerPosition();
        
        const newAnimations = new Map();
        
        // Use cards from the event data, not current centerPile state which may be empty
        const cardsToAnimate = action.data.center_pile_cards || centerPile;
        console.log('Cards to animate from BS call:', cardsToAnimate);
        
        // Animate all center pile cards to target player
        cardsToAnimate.forEach((card: any, index: number) => {
          // Handle both current centerPile format and event data format
          const cardId = card.id || `${card.suit}_${card.rank}`;
          const currentPilePos = getCenterPilePosition(index);
          
          newAnimations.set(cardId, {
            from: { 
              x: currentPilePos.x, 
              y: currentPilePos.y 
            },
            to: { 
              x: targetPlayerPos.x - centerContainerPos.x, 
              y: targetPlayerPos.y - centerContainerPos.y 
            }
          });
        });
        
        setAnimatingFromCenter(newAnimations);
        
        // Clear animations after they complete
        setTimeout(() => {
          setAnimatingFromCenter(new Map());
        }, 1000);
      }

      // Handle thought bubbles for player reasoning
      console.log('Checking for reasoning in action:', action.type, action.data);

      if (action.data && action.data.reasoning && action.data.reasoning.trim()) {
        const reasoningText = action.data.reasoning;
        
        // The secondary duplicate check for thought bubbles has been removed,
        // as the primary eventId check at the top of this useEffect hook is sufficient
        // to prevent processing the same event multiple times. This resolves the
        // double-animation trigger issue seen in development with React's Strict Mode.
        
        console.log('Showing thought bubble for:', playerId, 'reasoning:', reasoningText);
        
        setActiveThoughts(prevThoughts => {
          const newThoughts = new Map(prevThoughts);
          newThoughts.set(playerId, {
            reasoning: reasoningText,
            timestamp: Date.now()
          });
          return newThoughts;
        });
        
        // Mark this player as animating
        setAnimatingThoughts(prev => {
          const newAnimating = new Set(prev).add(playerId);
          console.log('🎬 Started animation for player:', playerId, 'Currently animating:', Array.from(newAnimating));
          return newAnimating;
        });
      } else {
        console.log('No reasoning found or empty reasoning for action:', action.type, 'data:', action.data);
      }
    }
  }, [lastGameEvent]);

  const getRankName = (rank: Rank): string => {
    const rankNames = {
      [Rank.ACE]: "Ace",
      [Rank.TWO]: "2",
      [Rank.THREE]: "3", 
      [Rank.FOUR]: "4",
      [Rank.FIVE]: "5",
      [Rank.SIX]: "6",
      [Rank.SEVEN]: "7",
      [Rank.EIGHT]: "8",
      [Rank.NINE]: "9",
      [Rank.TEN]: "10",
      [Rank.JACK]: "Jack",
      [Rank.QUEEN]: "Queen",
      [Rank.KING]: "King"
    };
    return rankNames[rank];
  };

  const getPlayerPosition = (index: number, total: number) => {
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
  };

  const getCenterContainerPosition = () => {
    const centerX = typeof window !== 'undefined' ? window.innerWidth / 2 : 800;
    const centerY = typeof window !== 'undefined' ? window.innerHeight / 2 : 400;
    
    return { x: centerX, y: centerY };
  };

  const getCardPosition = (playerIndex: number, cardIndex: number, totalCards: number, playersCount: number) => {
    const playerPos = getPlayerPosition(playerIndex, playersCount);
    const cardSpacing = 25;
    const startX = playerPos.x - (totalCards * cardSpacing) / 2;
    
    return {
      x: startX + cardIndex * cardSpacing,
      y: playerPos.y
    };
  };

  const getCenterPilePosition = (cardIndex: number) => {
    // Position cards in a small cluster around the center (relative to center container)
    const spread = 15; // Reduced spread for better visibility
    const angle = (cardIndex * 45) % 360; // Different angle for each card
    const distance = Math.min(cardIndex * 8, 25); // Spiral outward slightly
    
    return {
      x: Math.cos(angle * Math.PI / 180) * distance + (Math.random() - 0.5) * spread,
      y: Math.sin(angle * Math.PI / 180) * distance + (Math.random() - 0.5) * spread
    };
  };

  const formatActionMessage = (action: string) => {
    if (!action) return 'Waiting for action...';
    
    // Parse different types of actions and format them nicely
    if (action.includes('played') && action.includes('truthfully')) {
      return `✅ ${action}`;
    } else if (action.includes('played') && action.includes('bluffed')) {
      return `🎭 ${action}`;
    } else if (action.includes('incorrectly called BS')) {
      return `💥 ${action}`;
    } else if (action.includes('correctly called BS')) {
      return `🎯 ${action}`;
    } else if (action.includes('takes all center pile cards')) {
      return `📚 ${action}`;
    }
    
    return action;
  };

  // Handle thought bubble completion
  const handleThoughtBubbleComplete = (playerId: string) => {
    setActiveThoughts(prevThoughts => {
      const newThoughts = new Map(prevThoughts);
      newThoughts.delete(playerId);
      return newThoughts;
    });
    
    // Remove from animating thoughts when animation completes
    setAnimatingThoughts(prev => {
      const newAnimating = new Set(prev);
      newAnimating.delete(playerId);
      console.log('🎬 Completed animation for player:', playerId, 'Currently animating:', Array.from(newAnimating));
      return newAnimating;
    });
  };

  // Get the center container position for consistent positioning
  const centerContainerPos = getCenterContainerPosition();

  return (
    <div className="game-board relative w-full h-screen bg-gradient-to-br from-green-800 to-green-900 overflow-hidden touch-pan-y select-none" style={{ touchAction: 'pan-y' }}>
      {/* Floating terminal-style glassy header */}
      <motion.div 
        className="absolute top-6 left-1/2 transform -translate-x-1/2 z-10"
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
      >
        <div className="bg-black bg-opacity-20 backdrop-blur-lg border border-green-400 border-opacity-30 rounded-2xl px-8 py-6 shadow-2xl">
          <div className="flex items-center space-x-8 text-green-300 font-mono">
            <div className="text-xl font-bold flex items-center">
              <span className="ml-2 min-w-[120px]">
                {displayTurn}
                {isTyping && displayTurn.length < `Turn ${gameState.turn_number}`.length && (
                  <span className="animate-pulse">|</span>
                )}
              </span>
            </div>
            <div className="text-lg flex items-center">
              <span className="text-green-200">Expected:</span>
              <span className="ml-2 font-semibold text-yellow-300 min-w-[80px]">
                {displayRank}
                {isTyping && displayRank.length < getRankName(gameState.current_expected_rank).length && (
                  <span className="animate-pulse">|</span>
                )}
              </span>
            </div>
            {gameState.game_phase === 'game_over' && gameState.winner && (
              <div className="text-lg px-4 py-2 bg-yellow-500 bg-opacity-20 backdrop-blur-sm rounded-xl border border-yellow-400 border-opacity-40">
                <span className="text-yellow-300">🏆 {gameState.winner} wins!</span>
              </div>
            )}
          </div>
        </div>
      </motion.div>

      {/* Floating latest action */}
      <motion.div 
        className="absolute bottom-8 left-1/2 transform -translate-x-1/2 z-10"
        key={lastAction}
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
      >
        <div className="bg-black bg-opacity-40 backdrop-blur-lg border border-white border-opacity-20 rounded-2xl px-8 py-4 shadow-2xl max-w-4xl">
          <div className="text-white text-lg font-mono text-center">
            {formatActionMessage(lastAction) || 'Game starting...'}
          </div>
        </div>
      </motion.div>

      {/* Game content with zoom and pan */}
      <div
        style={{
          transform: `translate(${pan.x}px, ${pan.y}px) scale(${zoom})`,
          transformOrigin: 'center center',
          width: '100%',
          height: '100%'
        }}
      >
        {/* Player cards */}
        <AnimatePresence>
          {gameState.players.map((player, playerIndex) => {
            const playerCards = playerHands[player.id] || [];
            
            // Calculate position directly (no memoization needed in loop)
            const playerPos = getPlayerPosition(playerIndex, gameState.players.length);
            
            return (
              <div key={player.id} className="absolute">
                {/* Player info */}
                <motion.div 
                  className={`absolute text-white text-center font-bold p-3 rounded-lg shadow-lg ${
                    player.is_current_player ? 'bg-yellow-600 ring-2 ring-yellow-400' : 'bg-gray-700'
                  }`}
                  style={{
                    left: playerPos.x - 60,
                    top: playerPos.y - 80,
                    zIndex: 20
                  }}
                  animate={{
                    scale: player.is_current_player ? 1.1 : 1,
                    boxShadow: player.is_current_player ? '0 0 20px rgba(255, 255, 0, 0.5)' : '0 4px 6px rgba(0, 0, 0, 0.3)'
                  }}
                  transition={{ duration: 0.3 }}
                >
                  <div className="text-lg">{player.name}</div>
                  <div className="text-sm opacity-80">{player.hand_count} cards</div>
                  {player.is_current_player && (
                    <div className="text-xs text-yellow-200">Current Turn</div>
                  )}
                </motion.div>

                {/* Thought bubble with stable key and position */}
                {activeThoughts.has(player.id) && (
                  <ThoughtBubble
                    key={`${player.id}-${activeThoughts.get(player.id)?.timestamp}`}
                    playerId={player.id}
                    reasoning={activeThoughts.get(player.id)?.reasoning || ''}
                    position={playerPos}
                    onComplete={() => handleThoughtBubbleComplete(player.id)}
                  />
                )}
                
                {/* Player cards */}
                {playerCards.map((card, cardIndex) => {
                  const cardId = card.id;
                  const isAnimating = animatingCards.includes(cardId);
                  
                  return (
                    <motion.div
                      key={cardId}
                      initial={{ opacity: 1, scale: 1 }}
                      animate={{ 
                        opacity: isAnimating ? 0.3 : 1,
                        scale: isAnimating ? 0.8 : 1 
                      }}
                      transition={{ duration: 0.5 }}
                      style={{ position: 'absolute' }}
                    >
                      <Card
                        card={card}
                        isVisible={true}
                        position={getCardPosition(playerIndex, cardIndex, playerCards.length, gameState.players.length)}
                        scale={0.7}
                        rotation={0}
                        onClick={() => console.log(`Card clicked: ${card.id}`)}
                      />
                    </motion.div>
                  );
                })}
              </div>
            );
          })}
        </AnimatePresence>

        {/* Center pile - positioned using consistent coordinate system */}
        <div 
          className="absolute" 
          style={{ 
            left: centerContainerPos.x, 
            top: centerContainerPos.y, 
            transform: 'translate(-50%, -50%)' 
          }}
        >
          <motion.div 
            className="text-white text-center font-bold mb-4 text-xl"
            animate={{ scale: centerPile.length > 0 ? 1.1 : 1 }}
          >
            Center Pile ({centerPile.length} cards)
          </motion.div>
          <div className="relative">
            
            <AnimatePresence>
              {centerPile.map((card, index) => {
                const cardId = card.id;
                const isNewCard = newlyAddedCards.has(cardId);
                const animationToCenter = animatingToCenter.get(cardId);
                const animationFromCenter = animatingFromCenter.get(cardId);
                
                // Determine the animation behavior
                let initial, animate;
                
                if (isNewCard && animationToCenter) {
                  // New card animating to center - coordinates are already relative
                  initial = {
                    x: animationToCenter.from.x,
                    y: animationToCenter.from.y
                  };
                  animate = {
                    x: animationToCenter.to.x,
                    y: animationToCenter.to.y
                  };
                } else if (animationFromCenter) {
                  // Card animating from center (BS call) - coordinates are already relative
                  initial = {
                    x: animationFromCenter.from.x,
                    y: animationFromCenter.from.y
                  };
                  animate = {
                    x: animationFromCenter.to.x,
                    y: animationFromCenter.to.y
                  };
                } else {
                  // Static card in center pile - use relative coordinates directly
                  const staticPos = getCenterPilePosition(index);
                  initial = staticPos;
                  animate = staticPos;
                }
                
                return (
                  <motion.div
                    key={cardId}
                    initial={initial}
                    animate={animate}
                    exit={{ opacity: 0, scale: 0.8 }}
                    transition={{ 
                      duration: 0.8, 
                      ease: "easeInOut",
                      type: "spring",
                      stiffness: 100,
                      damping: 15
                    }}
                    style={{ position: 'absolute', zIndex: 10 + index }}
                  >
                    <Card
                      card={card}
                      isVisible={false} // Cards in center pile are face down
                      position={{ x: 0, y: 0 }} // Position handled by motion.div
                      scale={0.9}
                      rotation={Math.random() * 20 - 10}
                    />
                  </motion.div>
                );
              })}
            </AnimatePresence>
            
            {/* Center pile indicator */}
            {centerPile.length === 0 && (
              <div className="w-24 h-36 border-2 border-dashed border-white border-opacity-50 rounded-lg flex items-center justify-center">
                <span className="text-white text-opacity-50 text-sm">Empty</span>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default GameBoard; 