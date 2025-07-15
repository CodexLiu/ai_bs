import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

interface ThoughtBubbleProps {
  playerId: string;
  reasoning: string;
  position: { x: number; y: number };
  onComplete?: () => void;
}

const ThoughtBubble: React.FC<ThoughtBubbleProps> = ({ 
  playerId, 
  reasoning, 
  position, 
  onComplete 
}) => {
  const [displayText, setDisplayText] = useState('');
  const [isTyping, setIsTyping] = useState(true);
  const [showCursor, setShowCursor] = useState(true);

  useEffect(() => {
    if (!reasoning) return;

    // Don't restart animation if we're already displaying the same reasoning
    if (displayText === reasoning && !isTyping) {
      return;
    }

    let index = 0;
    setDisplayText('');
    setIsTyping(true);

    const typeInterval = setInterval(() => {
      if (index < reasoning.length) {
        setDisplayText(reasoning.substring(0, index + 1));
        index++;
      } else {
        setIsTyping(false);
        clearInterval(typeInterval);
        
        // Start fade out after 3 seconds
        setTimeout(() => {
          onComplete?.();
        }, 3000);
      }
    }, 20); // Typing speed - much faster

    return () => clearInterval(typeInterval);
  }, [reasoning, onComplete]);

  // Cursor blinking effect
  useEffect(() => {
    const cursorInterval = setInterval(() => {
      setShowCursor(prev => !prev);
    }, 500);

    return () => clearInterval(cursorInterval);
  }, []);

  if (!reasoning) return null;

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0, scale: 0.8, y: 20 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        exit={{ opacity: 0, scale: 0.8, y: -20 }}
        transition={{ 
          duration: 0.3,
          ease: "easeOut"
        }}
        className="absolute z-30 pointer-events-none"
        style={{
          left: position.x - 150, // Center the bubble
          top: position.y - 90,   // Position where bottom of bubble should be
          width: '300px',
          transform: 'translateY(-100%)' // Make bubble grow upward from this point
        }}
      >
        {/* Thought bubble tail */}
        <div className="relative">
          <div className="absolute bottom-0 left-1/2 transform -translate-x-1/2 translate-y-full">
            <div className="w-0 h-0 border-l-[15px] border-r-[15px] border-t-[20px] border-l-transparent border-r-transparent border-t-gray-900"></div>
          </div>
          
          {/* Main bubble */}
          <div className="bg-gray-900 border-2 border-green-400 rounded-lg p-4 shadow-2xl">
            {/* Terminal header */}
            <div className="flex items-center justify-between border-b border-green-400 pb-2 mb-3">
              <div className="flex items-center space-x-2">
                <div className="w-3 h-3 bg-red-500 rounded-full"></div>
                <div className="w-3 h-3 bg-yellow-500 rounded-full"></div>
                <div className="w-3 h-3 bg-green-500 rounded-full"></div>
              </div>
              <div className="text-green-400 text-xs font-mono">
                {playerId}_thoughts.log
              </div>
            </div>
            
            {/* Terminal content */}
            <div className="font-mono text-sm">
              <div className="text-green-400 mb-1">
                $ echo "{playerId} reasoning"
              </div>
              <div className="text-green-300 min-h-[20px] flex items-start">
                <span className="text-green-400 mr-2">{'>'}</span>
                <span className="flex-1">
                  {displayText}
                  {isTyping && showCursor && (
                    <span className="text-green-400 animate-pulse">▋</span>
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

export default ThoughtBubble; 