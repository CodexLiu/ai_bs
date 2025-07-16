import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

interface ReactionBubbleProps {
  playerId: string;
  reaction: string;
  position: { x: number; y: number };
  onComplete?: () => void;
}

const ReactionBubble: React.FC<ReactionBubbleProps> = ({ 
  playerId, 
  reaction, 
  position, 
  onComplete 
}) => {
  const [displayText, setDisplayText] = useState('');
  const [isTyping, setIsTyping] = useState(true);
  const [showCursor, setShowCursor] = useState(true);

  useEffect(() => {
    if (!reaction) return;

    // Don't restart animation if we're already displaying the same reaction
    if (displayText === reaction && !isTyping) {
      return;
    }

    let index = 0;
    setDisplayText('');
    setIsTyping(true);

    const typeInterval = setInterval(() => {
      if (index < reaction.length) {
        setDisplayText(reaction.substring(0, index + 1));
        index++;
      } else {
        setIsTyping(false);
        clearInterval(typeInterval);
        
        // Start minimize animation after 2 seconds (shorter than thought bubble)
        setTimeout(() => {
          onComplete?.();
        }, 2000);
      }
    }, 30); // Slightly slower typing speed for reactions

    return () => clearInterval(typeInterval);
  }, [reaction]);

  // Cursor blinking effect
  useEffect(() => {
    const cursorInterval = setInterval(() => {
      setShowCursor(prev => !prev);
    }, 500);

    return () => clearInterval(cursorInterval);
  }, []);

  if (!reaction) return null;

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0, scale: 0.8, y: 20 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        exit={{ 
          opacity: 0, 
          scale: 0.1, 
          x: -200, // Move towards the player card (to the left)
          y: 10,   // Slight downward movement
          rotate: -10 // Slight rotation for dynamic effect
        }}
        transition={{ 
          duration: 0.5,
          ease: "easeInOut",
          exit: {
            duration: 0.4,
            ease: "easeIn"
          }
        }}
        className="z-30 pointer-events-none"
        style={{
          width: '280px',
          minWidth: '280px',
          transform: `translate(${position.x}px, ${position.y}px)`
        }}
      >
        {/* Reaction bubble tail pointing left towards player card */}
        <div className="relative">
          <div className="absolute top-1/2 left-0 transform -translate-x-full -translate-y-1/2">
            <div className="w-0 h-0 border-t-[15px] border-b-[15px] border-r-[20px] border-t-transparent border-b-transparent border-r-orange-900"></div>
          </div>
          
          {/* Main bubble */}
          <div className="bg-orange-900 border-2 border-orange-400 rounded-lg p-4 shadow-2xl">
            {/* Reaction header */}
            <div className="flex items-center justify-between border-b border-orange-400 pb-2 mb-3">
              <div className="flex items-center space-x-2">
                <div className="w-3 h-3 bg-red-500 rounded-full"></div>
                <div className="w-3 h-3 bg-yellow-500 rounded-full"></div>
                <div className="w-3 h-3 bg-green-500 rounded-full"></div>
              </div>
              <div className="text-orange-400 text-xs font-mono">
                {playerId}_reaction.txt
              </div>
            </div>
            
            {/* Reaction content */}
            <div className="font-mono text-sm">
              <div className="text-orange-400 mb-1">
                $ echo "{playerId} reacts"
              </div>
              <div className="text-orange-300 min-h-[20px] flex items-start">
                <span className="text-orange-400 mr-2">{'>'}</span>
                <span className="flex-1 text-lg font-bold">
                  {displayText}
                  {isTyping && showCursor && (
                    <span className="text-orange-400 animate-pulse">▋</span>
                  )}
                </span>
              </div>
            </div>
          </div>
        </div>
      </motion.div>
    </AnimatePresence>
  );
};

export default ReactionBubble; 