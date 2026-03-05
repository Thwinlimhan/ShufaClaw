import os
import discord
from functools import wraps
import logging

logger = logging.getLogger('discord_agent.permissions')

def is_admin():
    """Check if the user invoking the command is the designated admin"""
    def predicate(interaction: discord.Interaction) -> bool:
        admin_id = os.environ.get("DISCORD_ADMIN_USER_ID")
        if not admin_id:
            logger.warning("No DISCORD_ADMIN_USER_ID set. Allowing all for now.")
            return True
        return str(interaction.user.id) == admin_id
    return discord.app_commands.check(predicate)
