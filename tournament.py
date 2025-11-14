import math
import random
from typing import Dict, List, Optional, Tuple

class TournamentManager:
    def __init__(self):
        self.tournaments: Dict[int, Dict] = {}  # guild_id -> tournament data
    
    def create_tournament(self, guild_id: int, name: str, max_participants: int, 
                         format: str, creator_id: int) -> Dict:
        """Create a new tournament"""
        tournament = {
            'name': name,
            'max_participants': max_participants,
            'format': format,
            'creator_id': creator_id,
            'status': 'registration',
            'participants': [],
            'participant_names': {},
            'bracket': None,
            'current_round': 0,
            'matches': {},
            'match_counter': 0
        }
        self.tournaments[guild_id] = tournament
        return tournament
    
    def get_active_tournament(self, guild_id: int) -> Optional[Dict]:
        """Get the active tournament for a guild"""
        return self.tournaments.get(guild_id)
    
    def add_participant(self, guild_id: int, user_id: int, display_name: str):
        """Add a participant to the tournament"""
        tournament = self.get_active_tournament(guild_id)
        if tournament and tournament['status'] == 'registration':
            if user_id not in tournament['participants']:
                tournament['participants'].append(user_id)
                tournament['participant_names'][user_id] = display_name
    
    def remove_participant(self, guild_id: int, user_id: int):
        """Remove a participant from the tournament"""
        tournament = self.get_active_tournament(guild_id)
        if tournament and tournament['status'] == 'registration':
            if user_id in tournament['participants']:
                tournament['participants'].remove(user_id)
                if user_id in tournament['participant_names']:
                    del tournament['participant_names'][user_id]
    
    def start_tournament(self, guild_id: int):
        """Start the tournament and generate bracket"""
        tournament = self.get_active_tournament(guild_id)
        if not tournament:
            return
        
        participants = tournament['participants'].copy()
        num_participants = len(participants)
        
        if num_participants < 2:
            return
        
        # Pad to next power of 2 with byes
        next_power_of_2 = 2 ** math.ceil(math.log2(num_participants))
        byes_needed = next_power_of_2 - num_participants
        
        # Add byes (None represents a bye)
        bracket_participants = participants + [None] * byes_needed
        
        # Generate bracket structure
        tournament['bracket'] = self._generate_bracket(bracket_participants)
        tournament['status'] = 'in_progress'
        tournament['current_round'] = 0
        tournament['match_counter'] = 0

        # Initialize matches
        self._initialize_matches(guild_id)
    
    def _generate_bracket(self, participants: List) -> List:
        """Generate a single elimination bracket structure"""
        # Shuffle for fairness
        random.shuffle(participants)
        
        # Create initial round matches
        round_matches = []
        for i in range(0, len(participants), 2):
            match = {
                'player1': participants[i],
                'player2': participants[i + 1] if i + 1 < len(participants) else None,
                'winner': None
            }
            round_matches.append(match)
        
        bracket = [round_matches]
        
        # Generate subsequent rounds
        while len(round_matches) > 1:
            next_round = []
            for i in range(0, len(round_matches), 2):
                match = {
                    'player1': None,  # Will be winner of previous match
                    'player2': None,
                    'winner': None
                }
                next_round.append(match)
            bracket.append(next_round)
            round_matches = next_round
        
        return bracket
    
    def _initialize_matches(self, guild_id: int):
        """Initialize match tracking"""
        tournament = self.get_active_tournament(guild_id)
        if not tournament or not tournament['bracket']:
            return
        
        match_id = 1
        for round_num, round_matches in enumerate(tournament['bracket']):
            for match_idx, match in enumerate(round_matches):
                tournament['matches'][match_id] = {
                    'round': round_num,
                    'match_index': match_idx,
                    'player1': match['player1'],
                    'player2': match['player2'],
                    'winner': None,
                    'completed': False,
                    'poll_message_id': None,
                    'poll_channel_id': None
                }
                match_id += 1
    
    def get_bracket(self, guild_id: int) -> Optional[List]:
        """Get the bracket structure"""
        tournament = self.get_active_tournament(guild_id)
        return tournament['bracket'] if tournament else None
    
    def format_bracket(self, guild_id: int) -> str:
        """Format the bracket as a string"""
        tournament = self.get_active_tournament(guild_id)
        if not tournament or not tournament['bracket']:
            return ""
        
        lines = []
        bracket = tournament['bracket']
        participant_names = tournament['participant_names']
        matches = tournament['matches']
        
        # Find match IDs for each bracket position
        match_id_map = {}
        match_id = 1
        for round_num, round_matches in enumerate(bracket):
            for match_idx in range(len(round_matches)):
                match_id_map[(round_num, match_idx)] = match_id
                match_id += 1
        
        # Format each round
        for round_num, round_matches in enumerate(bracket):
            round_name = f"Round {round_num + 1}"
            if round_num == len(bracket) - 1:
                round_name = "🏆 Finals"
            elif round_num == len(bracket) - 2:
                round_name = "🥈 Semi-Finals"
            elif round_num == len(bracket) - 3:
                round_name = "🥉 Quarter-Finals"
            
            lines.append(f"\n**{round_name}**")
            
            for match_idx, match in enumerate(round_matches):
                match_id = match_id_map.get((round_num, match_idx), 0)
                match_data = matches.get(match_id, {})
                
                # Get player names
                p1 = match.get('player1') or match_data.get('player1')
                p2 = match.get('player2') or match_data.get('player2')
                
                p1_name = self._get_player_name(p1, participant_names)
                p2_name = self._get_player_name(p2, participant_names)
                
                # Check if match is completed
                winner = match_data.get('winner')
                if winner:
                    winner_name = participant_names.get(winner, f"User {winner}")
                    if p1 == winner:
                        p1_name = f"✅ {p1_name}"
                    else:
                        p2_name = f"✅ {p2_name}"
                
                match_line = f"  Match {match_id}: {p1_name} vs {p2_name}"
                if match_data.get('completed'):
                    match_line += " ✓"
                
                lines.append(match_line)
        
        return "\n".join(lines)
    
    def _get_player_name(self, player_id, participant_names: Dict) -> str:
        """Get display name for a player"""
        if player_id is None:
            return "BYE"
        return participant_names.get(player_id, f"User {player_id}")
    
    def report_match_result(self, guild_id: int, match_id: int, winner_id: int) -> Dict:
        """Report the result of a match"""
        tournament = self.get_active_tournament(guild_id)
        if not tournament:
            return {'success': False, 'message': 'No active tournament'}
        
        if match_id not in tournament['matches']:
            return {'success': False, 'message': 'Invalid match ID'}
        
        match_data = tournament['matches'][match_id]
        
        if match_data['completed']:
            return {'success': False, 'message': 'Match already completed'}
        
        # Verify winner is a participant in this match
        if winner_id not in [match_data['player1'], match_data['player2']]:
            return {'success': False, 'message': 'Winner must be a participant in this match'}
        
        # Handle bye
        if match_data['player1'] is None:
            match_data['winner'] = match_data['player2']
        elif match_data['player2'] is None:
            match_data['winner'] = match_data['player1']
        else:
            match_data['winner'] = winner_id
        
        match_data['completed'] = True
        
        # Update bracket
        round_num = match_data['round']
        match_idx = match_data['match_index']
        tournament['bracket'][round_num][match_idx]['winner'] = winner_id
        
        # Advance winner to next round
        if round_num < len(tournament['bracket']) - 1:
            next_round = round_num + 1
            next_match_idx = match_idx // 2
            
            if next_match_idx < len(tournament['bracket'][next_round]):
                next_match = tournament['bracket'][next_round][next_match_idx]
                
                # Determine which position (player1 or player2) in next match
                position = 'player1' if match_idx % 2 == 0 else 'player2'
                next_match[position] = winner_id
                
                # Update match data
                next_match_id = self._get_match_id(tournament, next_round, next_match_idx)
                if next_match_id:
                    tournament['matches'][next_match_id][position] = winner_id
        
        # Check if tournament is complete
        final_round = len(tournament['bracket']) - 1
        if final_round >= 0:
            final_match = tournament['bracket'][final_round][0]
            if final_match.get('winner'):
                tournament['status'] = 'completed'
                return {
                    'success': True,
                    'message': 'Match result recorded',
                    'tournament_complete': True,
                    'next_round': round_num < len(tournament['bracket']) - 1
                }
        
        return {
            'success': True,
            'message': 'Match result recorded',
            'next_round': round_num < len(tournament['bracket']) - 1
        }
    
    def _get_match_id(self, tournament: Dict, round_num: int, match_idx: int) -> Optional[int]:
        """Get match ID from round and match index"""
        match_id = 1
        for r in range(len(tournament['bracket'])):
            for m in range(len(tournament['bracket'][r])):
                if r == round_num and m == match_idx:
                    return match_id
                match_id += 1
        return None
    
    def end_tournament(self, guild_id: int):
        """End the tournament"""
        tournament = self.get_active_tournament(guild_id)
        if tournament:
            tournament['status'] = 'completed'
    
    def is_tournament_complete(self, guild_id: int) -> bool:
        """Check if the tournament is complete"""
        tournament = self.get_active_tournament(guild_id)
        if not tournament or not tournament['bracket']:
            return False
        
        # Check if final match has a winner
        final_round = len(tournament['bracket']) - 1
        if final_round >= 0 and tournament['bracket'][final_round]:
            final_match = tournament['bracket'][final_round][0]
            return final_match.get('winner') is not None
        
        return tournament['status'] == 'completed'
    
    def reset_tournament(self, guild_id: int):
        """Reset/delete the tournament"""
        if guild_id in self.tournaments:
            del self.tournaments[guild_id]
    
    def get_ready_matches(self, guild_id: int, round_num: int) -> List[Dict]:
        """Get matches that are ready to be played (both players determined, not completed)"""
        tournament = self.get_active_tournament(guild_id)
        if not tournament or not tournament['bracket']:
            return []
        
        ready_matches = []
        for match_id, match_data in tournament['matches'].items():
            if (match_data['round'] == round_num and 
                not match_data['completed'] and
                match_data['player1'] is not None and
                match_data['player2'] is not None and
                match_data['poll_message_id'] is None):  # Poll not created yet
                ready_matches.append({
                    'match_id': match_id,
                    'player1': match_data['player1'],
                    'player2': match_data['player2'],
                    'round': round_num
                })
        
        return ready_matches
    
    def set_poll_info(self, guild_id: int, match_id: int, poll_message_id: int, poll_channel_id: int):
        """Store poll message and channel IDs for a match"""
        tournament = self.get_active_tournament(guild_id)
        if tournament and match_id in tournament['matches']:
            tournament['matches'][match_id]['poll_message_id'] = poll_message_id
            tournament['matches'][match_id]['poll_channel_id'] = poll_channel_id
    
    def get_match_by_poll(self, guild_id: int, poll_message_id: int) -> Optional[Dict]:
        """Get match data by poll message ID"""
        tournament = self.get_active_tournament(guild_id)
        if not tournament:
            return None
        
        for match_id, match_data in tournament['matches'].items():
            if match_data.get('poll_message_id') == poll_message_id:
                return {
                    'match_id': match_id,
                    'match_data': match_data,
                    'tournament': tournament
                }
        return None

class FakeTournamentManager(TournamentManager):
    def start_tournament(self, guild_id: int):
        """Start the tournament and generate bracket"""
        tournament = self.get_active_tournament(guild_id)
        if not tournament:
            return
        
        participants = tournament['participants'].copy()
        num_participants = len(participants)
        
        if num_participants < 2:
            return
        
        # Pad to next power of 2 with byes
        next_power_of_2 = 2 ** math.ceil(math.log2(num_participants))
        byes_needed = next_power_of_2 - num_participants
        
        # Add byes (None represents a bye)
        bracket_participants = participants + [None] * byes_needed
        bracket_dictionary = tournament['participant_names'].copy()
        for i in range(byes_needed):
            bracket_dictionary[(num_participants + i + 1)] = f"BYE {i + 1}"
        # Generate bracket structure
        tournament['bracket'] = self._generate_bracket(bracket_participants)
        tournament['status'] = 'in_progress'
        tournament['current_round'] = 0
        tournament['match_counter'] = 0

        # Initialize matches
        self._initialize_matches(guild_id)
    
    def add_participant(self, guild_id: int, seed: int, player_name: str):
        """Add a participant to the tournament"""
        tournament = self.get_active_tournament(guild_id)
        if tournament and tournament['status'] == 'registration':
            if seed not in tournament['participants']:
                tournament['participants'].append(seed)
                tournament['participant_names'][seed] = player_name

    def remove_participant(self, guild_id: int, player_name: str):
        """Remove a participant from the tournament"""
        tournament = self.get_active_tournament(guild_id)
        if tournament and tournament['status'] == 'registration':
            if player_name in tournament['participant_names'].values():
                seed = list(tournament['participant_names'].keys())[list(tournament['participant_names'].values()).index(player_name)]
                del tournament['participant_names'][seed]
                tournament['participants'].remove(seed)
    
    def _generate_bracket(self, participants: List) -> List:
        """Generate a single elimination bracket structure"""
        # Sort & Match by Seed
        bracket_list = sorted(participants.copy().items(), key=lambda x: x[0])

        # Create initial round matches
        round_matches = []
        for i in range(0, len(participants), 2):
            match = {
                'player1': participants[i],
                'player2': participants[len(participants) - i - 1] if i + 1 < len(participants) else None,
                'winner': None
            }
            round_matches.append(match)
        

        bracket = [round_matches]
        
        # Generate subsequent rounds
        while len(round_matches) > 1:
            next_round = []
            for i in range(0, len(round_matches), 2):
                match = {
                    'player1': None,  # Will be winner of previous match
                    'player2': None,
                    'winner': None
                }
                next_round.append(match)
            bracket.append(next_round)
            round_matches = next_round
        
        return bracket

    def pick_winner(self, player1_seed: int, player2_seed: int) -> int:
        if player1_seed <= 0:
            return player2_seed
        if player2_seed <= 0:
            return player1_seed
        pick_me = random.randint(1, player1_seed + player2_seed)
        if pick_me <= player1_seed:
            return player1_seed
        else:
            return player2_seed
    
    