# Discord Tournament Bot

A comprehensive Discord bot for managing tournaments among server members. Create, join, and manage single or double elimination tournaments with an easy-to-use interface.

## Features

- 🏆 Create tournaments with customizable participant limits
- 📝 Easy registration system for participants
- 🎯 Single elimination bracket generation
- 📊 Real-time bracket viewing
- ✅ Match result reporting
- 🎮 Support for up to 64 participants
- 🔄 Tournament reset and management

## Setup Instructions

### 1. Create a Discord Bot

1. Go to the [Discord Developer Portal](https://discord.com/developers/applications)
2. Click "New Application" and give it a name
3. Go to the "Bot" section
4. Click "Add Bot" and confirm
5. Under "Privileged Gateway Intents", enable:
   - ✅ Server Members Intent
   - ✅ Message Content Intent
6. Copy the bot token (you'll need this later)
7. Go to the "OAuth2" > "URL Generator" section
8. Select scopes:
   - ✅ `bot`
   - ✅ `applications.commands`
9. Select bot permissions:
   - ✅ Send Messages
   - ✅ Embed Links
   - ✅ Read Message History
   - ✅ Use Slash Commands
   - ✅ Add Reactions (for polls)
   - ✅ Use External Emojis (may be needed for polls)
10. Copy the generated URL and open it in your browser to invite the bot to your server

### 2. Install Dependencies

Make sure you have Python 3.8 or higher installed, then run:

```bash
pip install -r requirements.txt
```

### 3. Configure the Bot

1. Create a `.env` file in the project directory
2. Add your Discord bot token:

```
DISCORD_TOKEN=your_bot_token_here
```

**Important:** Never share your bot token or commit it to version control!

### 4. Run the Bot

```bash
python bot.py
```

You should see a message confirming the bot has logged in and synced commands.

## Commands

All commands use Discord's slash command interface. Type `/` in your server to see available commands:

### Tournament Management

- `/tournament_create` - Create a new tournament
  - `name`: Name of the tournament
  - `max_participants`: Maximum number of participants (2-64, default: 16)
  - `format`: Tournament format (single_elimination or double_elimination, default: single_elimination)

- `/tournament_join` - Join the current tournament

- `/tournament_leave` - Leave the current tournament (only during registration)

- `/tournament_start` - Start the tournament and generate the bracket (closes registration)

- `/tournament_status` - View the current tournament status and participants

- `/tournament_bracket` - View the tournament bracket

- `/tournament_result` - Report a match result
  - `match_id`: The match ID (shown in the bracket)
  - `winner`: The winner's mention or user ID

- `/tournament_end` - End the current tournament

- `/tournament_reset` - Reset/delete the current tournament

## Usage Example

1. **Create a tournament:**
   ```
   /tournament_create name:Summer Championship max_participants:8
   ```

2. **Members join:**
   ```
   /tournament_join
   ```

3. **Start the tournament:**
   ```
   /tournament_start
   ```

4. **View the bracket:**
   ```
   /tournament_bracket
   ```

5. **Report match results:**
   ```
   /tournament_result match_id:1 winner:@PlayerName
   ```

6. **Check status anytime:**
   ```
   /tournament_status
   ```

## Tournament Format

### Single Elimination
- Participants compete in a bracket
- One loss eliminates you
- Winner advances to the next round
- Continues until one champion remains

### Bracket Generation
- Automatically pads to the next power of 2
- Byes are given to some players in the first round if needed
- Bracket is randomly seeded for fairness

## Permissions

- Anyone can join/leave during registration
- Only the tournament creator or administrators can start/end/reset tournaments
- Anyone can view the bracket and status
- Match results can be reported by anyone (you may want to restrict this in the future)

## Troubleshooting

**Bot doesn't respond to commands:**
- Make sure the bot has the necessary permissions in your server
- Check that you've enabled the required intents in the Discord Developer Portal
- Verify the bot token is correct in your `.env` file

**Commands not showing up:**
- Wait a few minutes after starting the bot for commands to sync
- Try restarting the bot
- Make sure the bot has the `applications.commands` scope

**Tournament not working:**
- Make sure you have at least 2 participants before starting
- Check that registration is still open if trying to join

## Future Enhancements

Potential features to add:
- Double elimination bracket support (currently only structure exists)
- Automatic match scheduling
- Role-based permissions for match reporting
- Tournament history and statistics
- Prize pool management
- Integration with external tournament platforms

## License

This project is open source and available for personal use.

## Support

If you encounter any issues or have suggestions, please check the code comments or modify as needed for your use case.

