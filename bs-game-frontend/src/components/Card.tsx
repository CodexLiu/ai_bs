import React from 'react';
import { motion } from 'framer-motion';
import { Card as CardType, Suit, Rank } from '@/types/game';

interface CardProps {
  card: CardType;
  isVisible?: boolean;
  position?: { x: number; y: number };
  rotation?: number;
  scale?: number;
  onClick?: () => void;
  className?: string;
  style?: React.CSSProperties;
}

const getCardSVGId = (card: CardType): string => {
  const suitMap = {
    [Suit.HEARTS]: 'heart',
    [Suit.DIAMONDS]: 'diamond',
    [Suit.CLUBS]: 'club',
    [Suit.SPADES]: 'spade'
  };
  
  const rankMap = {
    [Rank.ACE]: '1',
    [Rank.TWO]: '2',
    [Rank.THREE]: '3',
    [Rank.FOUR]: '4',
    [Rank.FIVE]: '5',
    [Rank.SIX]: '6',
    [Rank.SEVEN]: '7',
    [Rank.EIGHT]: '8',
    [Rank.NINE]: '9',
    [Rank.TEN]: '10',
    [Rank.JACK]: 'jack',
    [Rank.QUEEN]: 'queen',
    [Rank.KING]: 'king'
  };
  
  return `${suitMap[card.suit]}_${rankMap[card.rank]}`;
};

const Card: React.FC<CardProps> = ({
  card,
  isVisible = true,
  position = { x: 0, y: 0 },
  rotation = 0,
  scale = 1,
  onClick,
  className = '',
  style = {}
}) => {
  const cardId = isVisible ? getCardSVGId(card) : 'back';
  
  return (
    <motion.div
      className={`card-container ${className}`}
      style={{
        position: 'absolute',
        left: position.x,
        top: position.y,
        cursor: onClick ? 'pointer' : 'default',
        ...style
      }}
      initial={{ scale: 0, opacity: 0 }}
      animate={{ 
        scale,
        rotate: rotation,
        opacity: 1
      }}
      transition={{ 
        type: 'spring',
        stiffness: 300,
        damping: 30
      }}
      onClick={onClick}
      whileHover={onClick ? { scale: scale * 1.05 } : {}}
      whileTap={onClick ? { scale: scale * 0.95 } : {}}
    >
      <svg
        width="84"
        height="122"
        viewBox="0 0 169.075 244.64"
        className="card-svg"
        style={{ filter: 'drop-shadow(2px 2px 4px rgba(0,0,0,0.2))' }}
      >
        <use href={`/svg-cards.svg#${cardId}`} />
      </svg>
    </motion.div>
  );
};

export default Card; 