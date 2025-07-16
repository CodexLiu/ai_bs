import random
from typing import Dict, List

class ReactionGenerator:
    def __init__(self):
        # Reactions for when AI player correctly calls BS
        self.correct_bs_call_reactions = [
            "F**k yeah! I knew you were lying!",
            "Holy sh*t, I actually caught you!",
            "HA! Got your a** red-handed!",
            "I f**king knew it! You're such a liar!",
            "Oh hell yeah! My gut was right!",
            "YES! I saw right through you!",
            "GOTCHA! You sneaky little trickster!",
            "I'm getting good at this!",
            "Take those cards, loser!",
            "Damn right I called you out!",
            "You thought you could fool me? Think again!",
            "I'm on fire! This feels amazing!",
            "Your poker face sucks, just saying",
            "BOOM! In your face!",
            "That's what you get for lying to me!",
            "I'm getting scary good at reading people",
            "Busted! I love being right!",
            "Justice served!",
            "I love being right about this stuff!",
            "Take that, you lying snake!"
        ]
        
        # Reactions for when AI player incorrectly calls BS
        self.incorrect_bs_call_reactions = [
            "Ah sh*t... I messed up big time",
            "God damn it! I was so wrong!",
            "F**k my life, I'm terrible at this",
            "Well, that was stupid of me",
            "Son of a b*tch! I feel like an idiot",
            "Ugh, I'm such a dummy!",
            "This is so embarrassing",
            "I hate myself right now, honestly",
            "Why did I do that? UGH!",
            "I'm a moron, aren't I?",
            "Damn it! I screwed up",
            "I feel like such an idiot",
            "That was really dumb of me",
            "I'm never living this down",
            "God, I'm so bad at this game",
            "This is exactly why I have trust issues",
            "I played myself like a fool",
            "I messed up so bad!",
            "I want to crawl under a rock and die",
            "I'm clearly terrible at reading people"
        ]
        
        # Reactions for when AI player gets BS called on them (caught bluffing)
        self.caught_bluffing_reactions = [
            "Oh sh*t, you got me good!",
            "F**k! I thought I was being smooth!",
            "Damn it, I'm a terrible liar!",
            "You sneaky b*stard, nice catch!",
            "My poker face is terrible!",
            "I'm garbage at bluffing, apparently",
            "I walked right into that!",
            "You're too good at this!",
            "I hate that you saw through me!",
            "I need to work on my lies",
            "I'm such a bad liar",
            "This is so frustrating!",
            "I thought I had you fooled!",
            "You're making me look like an amateur!",
            "I'm clearly not cut out for this",
            "I'm getting my butt kicked here",
            "God, I'm so transparent",
            "This is exactly why I don't gamble",
            "I feel like a complete failure right now",
            "I'll get you next time though!"
        ]
    
    def get_correct_bs_call_reaction(self) -> str:
        """Get a random reaction for when AI player correctly calls BS"""
        return random.choice(self.correct_bs_call_reactions)
    
    def get_incorrect_bs_call_reaction(self) -> str:
        """Get a random reaction for when AI player incorrectly calls BS"""
        return random.choice(self.incorrect_bs_call_reactions)
    
    def get_caught_bluffing_reaction(self) -> str:
        """Get a random reaction for when AI player gets caught bluffing"""
        return random.choice(self.caught_bluffing_reactions)
    
    def get_reaction_for_scenario(self, scenario: str) -> str:
        """
        Get a reaction based on the scenario
        
        Args:
            scenario: One of 'correct_bs_call', 'incorrect_bs_call', 'caught_bluffing'
            
        Returns:
            Random reaction message for the scenario
        """
        if scenario == "correct_bs_call":
            return self.get_correct_bs_call_reaction()
        elif scenario == "incorrect_bs_call":
            return self.get_incorrect_bs_call_reaction()
        elif scenario == "caught_bluffing":
            return self.get_caught_bluffing_reaction()
        else:
            return "What the heck just happened? 🤔"  # Default fallback 