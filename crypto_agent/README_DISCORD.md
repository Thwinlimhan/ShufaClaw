# Discord Bot Integration

## Setup Guide
1. Go to [Discord Developer Portal](https://discord.com/developers/applications) -> New Application -> "CryptoAgent"
2. Go to Bot tab -> Add Bot -> Copy TOKEN -> Paste to `.env` as `DISCORD_TOKEN`
3. Enable Privileged Gateway Intents: 
   - Message Content Intent
   - Server Members Intent
   - Presence Intent
4. Go to OAuth2 -> URL Generator
   - Scopes: `bot`, `applications.commands`
   - Bot Permissions: Send/Read Messages, Create Threads, Embed Links, Add Reactions, Manage Messages
5. Copy the generated URL and use it to invite the bot to your server.
6. Create server channels (and copy their IDs to `.env`):
   - `#crypto-agent`
   - `#price-alerts`
   - `#market-scanner`
   - `#morning-briefing`
   - `#journal`
   - `#signals`

## Running the bot
The bot will be started concurrently along with the main backend process. If you want to start it standalone:
`python discord_agent/bot.py`

## Commands
* `/price [coin]`
* `/market`
* `/ta [coin] [timeframe]`
* `/portfolio` (Private/Ephemeral)
* `/alert [coin] [direction] [price]`
* `/research [coin]`
* `/signals`
* `/briefing`
* `/journal`
* `/debate`
* `/scanner [on/off]`
* `/onchain`
