from enum import Enum
from dataclasses import dataclass
from typing import List, Optional
import random

class Suit(Enum):
    HEARTS = "hearts"
    DIAMONDS = "diamonds"
    CLUBS = "clubs"
    SPADES = "spades"

class Rank(Enum):
    ACE = 1
    TWO = 2
    THREE = 3
    FOUR = 4
    FIVE = 5
    SIX = 6
    SEVEN = 7
    EIGHT = 8
    NINE = 9
    TEN = 10
    JACK = 11
    QUEEN = 12
    KING = 13

@dataclass
class Card:
    suit: Suit
    rank: Rank
    
    def __str__(self) -> str:
        rank_names = {
            1: "Ace", 2: "2", 3: "3", 4: "4", 5: "5", 6: "6", 7: "7",
            8: "8", 9: "9", 10: "10", 11: "Jack", 12: "Queen", 13: "King"
        }
        return f"{rank_names[self.rank.value]} of {self.suit.value.title()}"
    
    def __repr__(self) -> str:
        return self.__str__()

class Deck:
    def __init__(self):
        self.cards: List[Card] = []
        self._create_deck()
    
    def _create_deck(self):
        """Create a standard 52-card deck"""
        self.cards = []
        for suit in Suit:
            for rank in Rank:
                self.cards.append(Card(suit, rank))
    
    def shuffle(self):
        """Shuffle the deck"""
        random.shuffle(self.cards)
    
    def deal_card(self) -> Optional[Card]:
        """Deal one card from the deck"""
        return self.cards.pop() if self.cards else None
    
    def deal_cards(self, count: int) -> List[Card]:
        """Deal multiple cards from the deck"""
        dealt_cards = []
        for _ in range(count):
            card = self.deal_card()
            if card:
                dealt_cards.append(card)
            else:
                break
        return dealt_cards
    
    def remaining_cards(self) -> int:
        """Get the number of cards remaining in the deck"""
        return len(self.cards)
    
    def is_empty(self) -> bool:
        """Check if the deck is empty"""
        return len(self.cards) == 0 