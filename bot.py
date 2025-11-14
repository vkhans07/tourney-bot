import discord
from discord.ext import commands
from discord import app_commands
import os
from dotenv import load_dotenv
from tournament import TournamentManager
import asyncio
from datetime import timedelta

# Load environment variables
load_dotenv()

# Bot setup
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True

bot = commands.Bot(command_prefix='!', intents=intents)
tournament_manager = TournamentManager()

@bot.event
async def on_ready():
    print(f'{bot.user} has logged in!')
    try:
        synced = await bot.tree.sync()
        print(f'Synced {len(synced)} command(s)')
    except Exception as e:
        print(f'Failed to sync commands: {e}')

@bot.tree.command(name="tournament_create", description="Create a new tournament")
@app_commands.describe(
    name="Name of the tournament",
    max_participants="Maximum number of participants (default: 16)",
    format="Tournament format: single_elimination or double_elimination (default: single_elimination)"
)
async def tournament_create(interaction: discord.Interaction, name: str, max_participants: int = 16, format: str = "single_elimination"):
    """Create a new tournament"""
    if format not in ["single_elimination", "double_elimination"]:
        await interaction.response.send_message("❌ Invalid format! Use `single_elimination` or `double_elimination`.", ephemeral=True)
        return
    
    if max_participants < 2 or max_participants > 64:
        await interaction.response.send_message("❌ Maximum participants must be between 2 and 64.", ephemeral=True)
        return
    
    tournament = tournament_manager.create_tournament(
        guild_id=interaction.guild_id,
        name=name,
        max_participants=max_participants,
        format=format,
        creator_id=interaction.user.id
    )
    
    embed = discord.Embed(
        title=f"🏆 Tournament Created: {name}",
        description=f"Tournament has been created successfully!",
        color=discord.Color.green()
    )
    embed.add_field(name="Format", value=format.replace("_", " ").title(), inline=True)
    embed.add_field(name="Max Participants", value=str(max_participants), inline=True)
    embed.add_field(name="Current Participants", value="0", inline=True)
    embed.add_field(name="Status", value="Registration Open", inline=False)
    embed.set_footer(text=f"Created by {interaction.user.display_name}")
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="tournament_join", description="Join the current tournament")
async def tournament_join(interaction: discord.Interaction):
    """Join the current tournament"""
    tournament = tournament_manager.get_active_tournament(interaction.guild_id)
    
    if not tournament:
        await interaction.response.send_message("❌ No active tournament found! Create one first with `/tournament_create`.", ephemeral=True)
        return
    
    if tournament['status'] != 'registration':
        await interaction.response.send_message(f"❌ Tournament registration is closed! Current status: {tournament['status']}", ephemeral=True)
        return
    
    if len(tournament['participants']) >= tournament['max_participants']:
        await interaction.response.send_message("❌ Tournament is full!", ephemeral=True)
        return
    
    if interaction.user.id in tournament['participants']:
        await interaction.response.send_message("❌ You're already registered for this tournament!", ephemeral=True)
        return
    
    tournament_manager.add_participant(interaction.guild_id, interaction.user.id, interaction.user.display_name)
    
    embed = discord.Embed(
        title="✅ Joined Tournament",
        description=f"You've successfully joined **{tournament['name']}**!",
        color=discord.Color.green()
    )
    embed.add_field(
        name="Participants", 
        value=f"{len(tournament['participants'])}/{tournament['max_participants']}", 
        inline=True
    )
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="tournament_leave", description="Leave the current tournament")
async def tournament_leave(interaction: discord.Interaction):
    """Leave the current tournament"""
    tournament = tournament_manager.get_active_tournament(interaction.guild_id)
    
    if not tournament:
        await interaction.response.send_message("❌ No active tournament found!", ephemeral=True)
        return
    
    if tournament['status'] != 'registration':
        await interaction.response.send_message("❌ Cannot leave tournament after registration has closed!", ephemeral=True)
        return
    
    if interaction.user.id not in tournament['participants']:
        await interaction.response.send_message("❌ You're not registered for this tournament!", ephemeral=True)
        return
    
    tournament_manager.remove_participant(interaction.guild_id, interaction.user.id)
    
    embed = discord.Embed(
        title="👋 Left Tournament",
        description=f"You've left **{tournament['name']}**.",
        color=discord.Color.orange()
    )
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="tournament_start", description="Start the tournament (closes registration)")
async def tournament_start(interaction: discord.Interaction):
    """Start the tournament"""
    tournament = tournament_manager.get_active_tournament(interaction.guild_id)
    
    if not tournament:
        await interaction.response.send_message("❌ No active tournament found!", ephemeral=True)
        return
    
    if tournament['creator_id'] != interaction.user.id and not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ Only the tournament creator or an administrator can start the tournament!", ephemeral=True)
        return
    
    if len(tournament['participants']) < 2:
        await interaction.response.send_message("❌ Need at least 2 participants to start a tournament!", ephemeral=True)
        return
    
    if tournament['status'] != 'registration':
        await interaction.response.send_message(f"❌ Tournament has already started! Current status: {tournament['status']}", ephemeral=True)
        return
    
    tournament_manager.start_tournament(interaction.guild_id)
    bracket = tournament_manager.get_bracket(interaction.guild_id)
    
    embed = discord.Embed(
        title=f"🚀 Tournament Started: {tournament['name']}",
        description="Registration is now closed and the bracket has been generated!",
        color=discord.Color.blue()
    )
    embed.add_field(name="Participants", value=str(len(tournament['participants'])), inline=True)
    embed.add_field(name="Format", value=tournament['format'].replace("_", " ").title(), inline=True)
    
    bracket_text = tournament_manager.format_bracket(interaction.guild_id)
    if bracket_text:
        embed.add_field(name="Bracket", value=bracket_text[:1024], inline=False)
    
    await interaction.response.send_message(embed=embed)
    
    # Handle byes (matches where one player gets a free pass)
    await handle_byes(interaction.guild_id, interaction.guild, interaction.channel)
    
    # Create polls for first round matches
    await create_polls_for_round(interaction.guild, interaction.channel, 0)

@bot.tree.command(name="tournament_status", description="View the current tournament status")
async def tournament_status(interaction: discord.Interaction):
    """View tournament status"""
    tournament = tournament_manager.get_active_tournament(interaction.guild_id)
    
    if not tournament:
        await interaction.response.send_message("❌ No active tournament found!", ephemeral=True)
        return
    
    status_emoji = {
        'registration': '📝',
        'in_progress': '⚔️',
        'completed': '🏆'
    }
    
    embed = discord.Embed(
        title=f"{status_emoji.get(tournament['status'], '❓')} {tournament['name']}",
        color=discord.Color.blue()
    )
    embed.add_field(name="Status", value=tournament['status'].replace("_", " ").title(), inline=True)
    embed.add_field(name="Format", value=tournament['format'].replace("_", " ").title(), inline=True)
    embed.add_field(name="Participants", value=f"{len(tournament['participants'])}/{tournament['max_participants']}", inline=True)
    
    if tournament['participants']:
        participant_list = []
        for user_id in tournament['participants']:
            user = bot.get_user(user_id)
            name = user.display_name if user else tournament['participant_names'].get(user_id, f"User {user_id}")
            participant_list.append(f"• {name}")
        
        participants_text = "\n".join(participant_list[:20])
        if len(participant_list) > 20:
            participants_text += f"\n... and {len(participant_list) - 20} more"
        
        embed.add_field(name="Registered Players", value=participants_text, inline=False)
    
    if tournament['status'] != 'registration':
        bracket_text = tournament_manager.format_bracket(interaction.guild_id)
        if bracket_text:
            embed.add_field(name="Bracket", value=bracket_text[:1024], inline=False)
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="tournament_bracket", description="View the tournament bracket")
async def tournament_bracket(interaction: discord.Interaction):
    """View the tournament bracket"""
    tournament = tournament_manager.get_active_tournament(interaction.guild_id)
    
    if not tournament:
        await interaction.response.send_message("❌ No active tournament found!", ephemeral=True)
        return
    
    if tournament['status'] == 'registration':
        await interaction.response.send_message("❌ Tournament hasn't started yet! Use `/tournament_start` to begin.", ephemeral=True)
        return
    
    bracket_text = tournament_manager.format_bracket(interaction.guild_id)
    
    if not bracket_text:
        await interaction.response.send_message("❌ Bracket not available yet!", ephemeral=True)
        return
    
    embed = discord.Embed(
        title=f"📊 Bracket: {tournament['name']}",
        description=bracket_text,
        color=discord.Color.purple()
    )
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="tournament_result", description="Report a match result")
@app_commands.describe(
    match_id="The match ID (shown in bracket)",
    winner="The winner's user ID or mention"
)
async def tournament_result(interaction: discord.Interaction, match_id: int, winner: discord.Member):
    """Report a match result"""
    tournament = tournament_manager.get_active_tournament(interaction.guild_id)
    
    if not tournament:
        await interaction.response.send_message("❌ No active tournament found!", ephemeral=True)
        return
    
    if tournament['status'] != 'in_progress':
        await interaction.response.send_message(f"❌ Tournament is not in progress! Current status: {tournament['status']}", ephemeral=True)
        return
    
    result = tournament_manager.report_match_result(interaction.guild_id, match_id, winner.id)
    
    if not result['success']:
        await interaction.response.send_message(f"❌ {result['message']}", ephemeral=True)
        return
    
    embed = discord.Embed(
        title="✅ Match Result Recorded",
        description=f"**{winner.display_name}** wins match {match_id}!",
        color=discord.Color.green()
    )
    
    if result.get('tournament_complete'):
        embed.add_field(name="🏆 Tournament Complete!", value=f"**{winner.display_name}** is the champion!", inline=False)
    
    await interaction.response.send_message(embed=embed)
    
    # Update bracket display
    if result.get('next_round'):
        bracket_text = tournament_manager.format_bracket(interaction.guild_id)
        if bracket_text:
            update_embed = discord.Embed(
                title=f"📊 Updated Bracket: {tournament['name']}",
                description=bracket_text,
                color=discord.Color.purple()
            )
            await interaction.followup.send(embed=update_embed)
        
        # Check if next round matches are ready and create polls
        match_data = tournament_manager.get_active_tournament(interaction.guild_id)['matches'][match_id]
        next_round = match_data['round'] + 1
        await create_polls_for_round(interaction.guild, interaction.channel, next_round)

@bot.tree.command(name="tournament_end", description="End the current tournament")
async def tournament_end(interaction: discord.Interaction):
    """End the current tournament"""
    tournament = tournament_manager.get_active_tournament(interaction.guild_id)
    
    if not tournament:
        await interaction.response.send_message("❌ No active tournament found!", ephemeral=True)
        return
    
    if tournament['creator_id'] != interaction.user.id and not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ Only the tournament creator or an administrator can end the tournament!", ephemeral=True)
        return
    
    tournament_manager.end_tournament(interaction.guild_id)
    
    embed = discord.Embed(
        title="🏁 Tournament Ended",
        description=f"**{tournament['name']}** has been ended.",
        color=discord.Color.red()
    )
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="tournament_reset", description="Reset/delete the current tournament")
async def tournament_reset(interaction: discord.Interaction):
    """Reset the current tournament"""
    tournament = tournament_manager.get_active_tournament(interaction.guild_id)
    
    if not tournament:
        await interaction.response.send_message("❌ No active tournament found!", ephemeral=True)
        return
    
    if tournament['creator_id'] != interaction.user.id and not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ Only the tournament creator or an administrator can reset the tournament!", ephemeral=True)
        return
    
    tournament_manager.reset_tournament(interaction.guild_id)
    
    embed = discord.Embed(
        title="🔄 Tournament Reset",
        description="The tournament has been reset. You can create a new one with `/tournament_create`.",
        color=discord.Color.orange()
    )
    
    await interaction.response.send_message(embed=embed)

async def handle_byes(guild_id: int, guild: discord.Guild, channel: discord.TextChannel):
    """Automatically handle matches with byes (one player gets a free pass)"""
    tournament = tournament_manager.get_active_tournament(guild_id)
    if not tournament:
        return
    
    # Check all matches in round 0 for byes
    for match_id, match_data in tournament['matches'].items():
        if match_data['round'] == 0 and not match_data['completed']:
            # Check if one player is None (bye)
            if match_data['player1'] is None and match_data['player2'] is not None:
                # Player 2 gets a bye
                tournament_manager.report_match_result(guild_id, match_id, match_data['player2'])
            elif match_data['player2'] is None and match_data['player1'] is not None:
                # Player 1 gets a bye
                tournament_manager.report_match_result(guild_id, match_id, match_data['player1'])

async def create_polls_for_round(guild: discord.Guild, channel: discord.TextChannel, round_num: int):
    """Create polls for all ready matches in a round"""
    tournament = tournament_manager.get_active_tournament(guild.id)
    if not tournament:
        return
    
    ready_matches = tournament_manager.get_ready_matches(guild.id, round_num)
    
    for match_info in ready_matches:
        match_id = match_info['match_id']
        player1_id = match_info['player1']
        player2_id = match_info['player2']
        
        # Get player names
        player1_name = tournament['participant_names'].get(player1_id, f"User {player1_id}")
        player2_name = tournament['participant_names'].get(player2_id, f"User {player2_id}")
        
        # Get user objects for mentions
        player1_user = guild.get_member(player1_id)
        player2_user = guild.get_member(player2_id)
        
        # Use display names if available
        if player1_user:
            player1_name = player1_user.display_name
        if player2_user:
            player2_name = player2_user.display_name
        
        # Create poll
        poll = discord.Poll(
            question=f"Match {match_id}: Who wins?",
            answers=[
                discord.PollAnswer(text=player1_name),
                discord.PollAnswer(text=player2_name)
            ],
            duration=timedelta(hours=24),  # Poll lasts 24 hours
            allow_multiselect=False
        )
        
        try:
            message = await channel.send(
                content=f"🏆 **{tournament['name']}** - Match {match_id}\n"
                       f"**{player1_name}** vs **{player2_name}**\n"
                       f"Vote for the winner!",
                poll=poll
            )
            
            # Store poll info
            tournament_manager.set_poll_info(guild.id, match_id, message.id, channel.id)
            
        except Exception as e:
            print(f"Error creating poll for match {match_id}: {e}")

@bot.event
async def on_raw_poll_vote_update(payload: discord.RawPollVoteUpdateEvent):
    """Handle poll vote updates - automatically check results when poll ends"""
    # Check if this poll is associated with a tournament match
    match_info = tournament_manager.get_match_by_poll(payload.guild_id, payload.message_id)
    
    if match_info:
        # Wait a bit to ensure poll state is updated
        await asyncio.sleep(2)
        
        try:
            guild = bot.get_guild(payload.guild_id)
            if not guild:
                return
            
            channel = guild.get_channel(payload.channel_id)
            if not channel:
                return
            
            message = await channel.fetch_message(payload.message_id)
            if not message.poll:
                return
            
            poll = message.poll
            match_data = match_info['match_data']
            tournament = match_info['tournament']
            
            # Only process if poll has ended or has a clear winner
            poll_ended = poll.expires_at and poll.expires_at < discord.utils.utcnow()
            
            if poll_ended or (poll.results and len(poll.results.answers) >= 2):
                answer1_votes = poll.results.answers[0].vote_count if poll.results else 0
                answer2_votes = poll.results.answers[1].vote_count if poll.results else 0
                
                # Determine winner
                if poll_ended:
                    # When poll ends, use majority vote (or first if tie)
                    if answer1_votes >= answer2_votes and answer1_votes > 0:
                        winner_id = match_data['player1']
                    elif answer2_votes > answer1_votes:
                        winner_id = match_data['player2']
                    else:
                        return  # No votes
                else:
                    # Poll still active - only update if clear winner
                    if answer1_votes > answer2_votes and answer1_votes > 0:
                        winner_id = match_data['player1']
                    elif answer2_votes > answer1_votes and answer2_votes > 0:
                        winner_id = match_data['player2']
                    else:
                        return  # Tie or no clear winner
                
                # Report the match result
                if not match_data['completed']:
                    result = tournament_manager.report_match_result(
                        payload.guild_id,
                        match_info['match_id'],
                        winner_id
                    )
                    
                    if result['success']:
                        winner_name = tournament['participant_names'].get(winner_id, f"User {winner_id}")
                        winner_user = guild.get_member(winner_id)
                        if winner_user:
                            winner_name = winner_user.display_name
                        
                        # Update poll message
                        await message.edit(
                            content=f"🏆 **{tournament['name']}** - Match {match_info['match_id']} ✅\n"
                                   f"**{tournament['participant_names'].get(match_data['player1'], 'Player 1')}** vs "
                                   f"**{tournament['participant_names'].get(match_data['player2'], 'Player 2')}**\n"
                                   f"**Winner: {winner_name}** 🎉"
                        )
                        
                        # Create polls for next round if ready
                        if result.get('next_round'):
                            next_round = match_data['round'] + 1
                            await create_polls_for_round(guild, channel, next_round)
                        
        except Exception as e:
            print(f"Error processing poll update: {e}")

@bot.tree.command(name="tournament_check_polls", description="Check poll results and update match winners")
async def tournament_check_polls(interaction: discord.Interaction):
    """Check all active polls and update match results"""
    tournament = tournament_manager.get_active_tournament(interaction.guild_id)
    
    if not tournament:
        await interaction.response.send_message("❌ No active tournament found!", ephemeral=True)
        return
    
    if tournament['status'] != 'in_progress':
        await interaction.response.send_message("❌ Tournament is not in progress!", ephemeral=True)
        return
    
    updated_matches = []
    
    # Check all matches with polls
    for match_id, match_data in tournament['matches'].items():
        if (match_data.get('poll_message_id') and 
            not match_data['completed'] and
            match_data['player1'] is not None and
            match_data['player2'] is not None):
            
            try:
                channel = interaction.guild.get_channel(match_data['poll_channel_id'])
                if not channel:
                    continue
                
                message = await channel.fetch_message(match_data['poll_message_id'])
                if not message.poll:
                    continue
                
                # Get poll results
                poll = message.poll
                # Check if poll has ended or has results
                if poll.expires_at and poll.expires_at < discord.utils.utcnow():
                    # Poll has ended, check results
                    if poll.results and len(poll.results.answers) >= 2:
                        answer1_votes = poll.results.answers[0].vote_count
                        answer2_votes = poll.results.answers[1].vote_count
                        
                        # Determine winner based on votes
                        if answer1_votes > answer2_votes:
                            winner_id = match_data['player1']
                        elif answer2_votes > answer1_votes:
                            winner_id = match_data['player2']
                        else:
                            # Tie - skip for now
                            continue
                    else:
                        continue
                elif poll.results and len(poll.results.answers) >= 2:
                    # Poll still active but has votes - check for clear winner
                    answer1_votes = poll.results.answers[0].vote_count
                    answer2_votes = poll.results.answers[1].vote_count
                    
                    # Only update if there's a clear winner (at least 1 vote difference)
                    if answer1_votes > answer2_votes and answer1_votes > 0:
                        winner_id = match_data['player1']
                    elif answer2_votes > answer1_votes and answer2_votes > 0:
                        winner_id = match_data['player2']
                    else:
                        # Tie or no votes - skip
                        continue
                else:
                    continue
                
                # Report the match result
                result = tournament_manager.report_match_result(
                    interaction.guild_id, 
                    match_id, 
                    winner_id
                )
                
                if result['success']:
                    updated_matches.append(match_id)
                    
                    winner_name = tournament['participant_names'].get(winner_id, f"User {winner_id}")
                    winner_user = interaction.guild.get_member(winner_id)
                    if winner_user:
                        winner_name = winner_user.display_name
                    
                    # Update poll message
                    await message.edit(
                        content=f"🏆 **{tournament['name']}** - Match {match_id} ✅\n"
                               f"**{tournament['participant_names'].get(match_data['player1'], 'Player 1')}** vs "
                               f"**{tournament['participant_names'].get(match_data['player2'], 'Player 2')}**\n"
                               f"**Winner: {winner_name}** 🎉"
                    )
                    
            except Exception as e:
                print(f"Error checking poll for match {match_id}: {e}")
                continue
    
    if updated_matches:
        embed = discord.Embed(
            title="✅ Poll Results Updated",
            description=f"Updated {len(updated_matches)} match(es): {', '.join(f'Match {m}' for m in updated_matches)}",
            color=discord.Color.green()
        )
        
        # Check if next round matches are ready
        if updated_matches:
            # Find the highest round that had matches updated
            max_round = max(tournament['matches'][m]['round'] for m in updated_matches)
            next_round = max_round + 1
            
            # Create polls for next round if ready
            await create_polls_for_round(interaction.guild, interaction.channel, next_round)
        
        await interaction.response.send_message(embed=embed)
    else:
        await interaction.response.send_message("ℹ️ No poll results to update yet. Polls may still be active or tied.", ephemeral=True)

# Run the bot
if __name__ == "__main__":
    token = os.getenv('DISCORD_TOKEN')
    if not token:
        print("❌ DISCORD_TOKEN not found in environment variables!")
        print("Please create a .env file with your Discord bot token.")
    else:
        bot.run(token)

