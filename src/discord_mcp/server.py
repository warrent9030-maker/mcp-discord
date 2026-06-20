import os
import sys
import asyncio
import logging
from datetime import datetime
from typing import Any, List
from functools import wraps
import discord
from discord.ext import commands
from mcp.server import Server
from mcp.types import Tool, TextContent
from mcp.server.stdio import stdio_server
from starlette.applications import Starlette
from starlette.routing import Route
from starlette.responses import JSONResponse
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware
import json
import aiohttp

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("discord-mcp-server")

# Discord bot setup
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
AUTH_TOKEN = os.getenv("MCP_AUTH_TOKEN") # Secure token for SSE access

if not DISCORD_TOKEN:
    raise ValueError("DISCORD_TOKEN environment variable is required")

# Initialize Discord bot with necessary intents
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Initialize MCP server
app = Server("discord-server")

# Store Discord client reference
discord_client = None

@bot.event
async def on_ready():
    global discord_client
    discord_client = bot
    logger.info(f"Logged in as {bot.user.name}")

# Helper function to ensure Discord client is ready
def require_discord_client(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        if not discord_client:
            raise RuntimeError("Discord client not ready")
        return await func(*args, **kwargs)
    return wrapper

class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        if not AUTH_TOKEN:
            return await call_next(request)
        
        # Check Authorization header or auth_token query param
        auth_header = request.headers.get("Authorization")
        query_token = request.query_params.get("auth_token")
        
        provided_token = None
        if auth_header and auth_header.startswith("Bearer "):
            provided_token = auth_header.split(" ")[1]
        elif query_token:
            provided_token = query_token
            
        if provided_token != AUTH_TOKEN:
            return JSONResponse({"error": "Unauthorized"}, status_code=401)
            
        return await call_next(request)

@app.list_tools()
async def list_tools() -> List[Tool]:
    \"\"\"List available Discord tools.\"\"\"
    return [
        Tool(
            name="get_server_info",
            description="Get information about a Discord server",
            inputSchema={
                "type": "object",
                "properties": {
                    "server_id": {
                        "type": "string",
                        "description": "Discord server (guild) ID"
                    }
                },
                "required": ["server_id"]
            }
        ),
        Tool(
            name="get_channels",
            description="Get a list of all channels in a Discord server",
            inputSchema={
                "type": "object",
                "properties": {
                    "server_id": {
                        "type": "string",
                        "description": "Discord server (guild) ID"
                    }
                },
                "required": ["server_id"]
            }
        ),
        Tool(
            name="list_members",
            description="Get a list of members in a server",
            inputSchema={
                "type": "object",
                "properties": {
                    "server_id": {
                        "type": "string",
                        "description": "Discord server (guild) ID"
                    },
                    "limit": {
                        "type": "number",
                        "description": "Maximum number of members to fetch",
                        "minimum": 1,
                        "maximum": 1000
                    }
                },
                "required": ["server_id"]
            }
        ),
        Tool(
            name="add_role",
            description="Add a role to a user",
            inputSchema={
                "type": "object",
                "properties": {
                    "server_id": {
                        "type": "string",
                        "description": "Discord server ID"
                    },
                    "user_id": {
                        "type": "string",
                        "description": "User to add role to"
                    },
                    "role_id": {
                        "type": "string",
                        "description": "Role ID to add"
                    }
                },
                "required": ["server_id", "user_id", "role_id"]
            }
        ),
        Tool(
            name="remove_role",
            description="Remove a role from a user",
            inputSchema={
                "type": "object",
                "properties": {
                    "server_id": {
                        "type": "string",
                        "description": "Discord server ID"
                    },
                    "user_id": {
                        "type": "string",
                        "description": "User to remove role from"
                    },
                    "role_id": {
                        "type": "string",
                        "description": "Role ID to remove"
                    }
                },
                "required": ["server_id", "user_id", "role_id"]
            }
        ),
        Tool(
            name="create_text_channel",
            description="Create a new text channel",
            inputSchema={
                "type": "object",
                "properties": {
                    "server_id": {
                        "type": "string",
                        "description": "Discord server ID"
                    },
                    "name": {
                        "type": "string",
                        "description": "Channel name"
                    },
                    "category_id": {
                        "type": "string",
                        "description": "Optional category ID to place channel in"
                    },
                    "topic": {
                        "type": "string",
                        "description": "Optional channel topic"
                    }
                },
                "required": ["server_id", "name"]
            }
        ),
        Tool(
            name="delete_channel",
            description="Delete a channel",
            inputSchema={
                "type": "object",
                "properties": {
                    "channel_id": {
                        "type": "string",
                        "description": "ID of channel to delete"
                    },
                    "reason": {
                        "type": "string",
                        "description": "Reason for deletion"
                    }
                },
                "required": ["channel_id"]
            }
        ),
        Tool(
            name="add_reaction",
            description="Add a reaction to a message",
            inputSchema={
                "type": "object",
                "properties": {
                    "channel_id": {
                        "type": "string",
                        "description": "Channel containing the message"
                    },
                    "message_id": {
                        "type": "string",
                        "description": "Message to react to"
                    },
                    "emoji": {
                        "type": "string",
                        "description": "Emoji to react with (Unicode or custom emoji ID)"
                    }
                },
                "required": ["channel_id", "message_id", "emoji"]
            }
        ),
        Tool(
            name="add_multiple_reactions",
            description="Add multiple reactions to a message",
            inputSchema={
                "type": "object",
                "properties": {
                    "channel_id": {
                        "type": "string",
                        "description": "Channel containing the message"
                    },
                    "message_id": {
                        "type": "string",
                        "description": "Message to react to"
                    },
                    "emojis": {
                        "type": "array",
                        "items": {
                            "type": "string",
                            "description": "Emoji to react with (Unicode or custom emoji ID)"
                        },
                        "description": "List of emojis to add as reactions"
                    }
                },
                "required": ["channel_id", "message_id", "emojis"]
            }
        ),
        Tool(
            name="remove_reaction",
            description="Remove a reaction from a message",
            inputSchema={
                "type": "object",
                "properties": {
                    "channel_id": {
                        "type": "string",
                        "description": "Channel containing the message"
                    },
                    "message_id": {
                        "type": "string",
                        "description": "Message to remove reaction from"
                    },
                    "emoji": {
                        "type": "string",
                        "description": "Emoji to remove (Unicode or custom emoji ID)"
                    }
                },
                "required": ["channel_id", "message_id", "emoji"]
            }
        ),
        Tool(
            name="send_message",
            description="Send a message to a specific channel",
            inputSchema={
                "type": "object",
                "properties": {
                    "channel_id": {
                        "type": "string",
                        "description": "Discord channel ID"
                    },
                    "content": {
                        "type": "string",
                        "description": "Message content"
                    }
                },
                "required": ["channel_id", "content"]
            }
        ),
        Tool(
            name="read_messages",
            description="Read recent messages from a channel",
            inputSchema={
                "type": "object",
                "properties": {
                    "channel_id": {
                        "type": "string",
                        "description": "Discord channel ID"
                    },
                    "limit": {
                        "type": "number",
                        "description": "Number of messages to fetch (max 100)",
                        "minimum": 1,
                        "maximum": 100
                    }
                },
                "required": ["channel_id"]
            }
        ),
        Tool(
            name="get_user_info",
            description="Get information about a Discord user",
            inputSchema={
                "type": "object",
                "properties": {
                    "user_id": {
                        "type": "string",
                        "description": "Discord user ID"
                    }
                },
                "required": ["user_id"]
            }
        ),
        Tool(
            name="moderate_message",
            description="Delete a message and optionally timeout the user",
            inputSchema={
                "type": "object",
                "properties": {
                    "channel_id": {
                        "type": "string",
                        "description": "Channel ID containing the message"
                    },
                    "message_id": {
                        "type": "string",
                        "description": "ID of message to moderate"
                    },
                    "reason": {
                        "type": "string",
                        "description": "Reason for moderation"
                    },
                    "timeout_minutes": {
                        "type": "number",
                        "description": "Optional timeout duration in minutes",
                        "minimum": 0,
                        "maximum": 40320
                    }
                },
                "required": ["channel_id", "message_id", "reason"]
            }
        ),
        Tool(
            name="list_servers",
            description="Get a list of all Discord servers the bot has access to.",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        Tool(
            name="list_roles",
            description="Get a list of all roles in a Discord server including permissions",
            inputSchema={
                "type": "object",
                "properties": {
                    "server_id": {
                        "type": "string",
                        "description": "Discord server (guild) ID"
                    }
                },
                "required": ["server_id"]
            }
        )
    ]

@app.call_tool()
@require_discord_client
async def call_tool(name: str, arguments: Any) -> List[TextContent]:
    if name == "send_message":
        channel = await discord_client.fetch_channel(int(arguments["channel_id"]))
        message = await channel.send(arguments["content"])
        return [TextContent(type="text", text=f"Message sent successfully. Message ID: {message.id}")]
    elif name == "read_messages":
        channel = await discord_client.fetch_channel(int(arguments["channel_id"]))
        limit = min(int(arguments.get("limit", 10)), 100)
        messages = []
        async for message in channel.history(limit=limit):
            reaction_data = [{\"emoji\": str(r.emoji), \"count\": r.count} for r in message.reactions]
            messages.append({
                "id": str(message.id),
                "author": str(message.author),
                "content": message.content,
                "timestamp": message.created_at.isoformat(),
                "reactions": reaction_data
            })
        return [TextContent(type="text", text="\\n".join([f\"{m['author']}: {m['content']}\" for m in messages]))]
    elif name == "get_user_info":
        user = await discord_client.fetch_user(int(arguments["user_id"]))
        return [TextContent(type="text", text=f"User: {user.name}#{user.discriminator} ({user.id})")]
    elif name == "moderate_message":
        channel = await discord_client.fetch_channel(int(arguments["channel_id"]))
        message = await channel.fetch_message(int(arguments["message_id"]))
        await message.delete(reason=arguments["reason"])
        return [TextContent(type="text", text="Message deleted.")]
    elif name == "get_server_info":
        guild = await discord_client.fetch_guild(int(arguments["server_id"]))
        return [TextContent(type="text", text=f"Server: {guild.name} ({guild.id})")]
    elif name == "get_channels":
        guild = discord_client.get_guild(int(arguments["server_id"]))
        channels = [f\"#{c.name} ({c.id})\" for c in guild.channels]
        return [TextContent(type="text", text="\\n".join(channels))]
    elif name == "list_members":
        guild = await discord_client.fetch_guild(int(arguments["server_id"]))
        members = []
        async for member in guild.fetch_members(limit=100):
            members.append(f\"{member.name} ({member.id})\")
        return [TextContent(type="text", text="\\n".join(members))]
    elif name == "add_role":
        guild = await discord_client.fetch_guild(int(arguments["server_id"]))
        member = await guild.fetch_member(int(arguments["user_id"]))
        role = guild.get_role(int(arguments["role_id"]))
        await member.add_roles(role)
        return [TextContent(type="text", text="Role added.")]
    elif name == "remove_role":
        guild = await discord_client.fetch_guild(int(arguments["server_id"]))
        member = await guild.fetch_member(int(arguments["user_id"]))
        role = guild.get_role(int(arguments["role_id"]))
        await member.remove_roles(role)
        return [TextContent(type="text", text="Role removed.")]
    elif name == "create_text_channel":
        guild = await discord_client.fetch_guild(int(arguments["server_id"]))
        channel = await guild.create_text_channel(name=arguments["name"])
        return [TextContent(type="text", text=f"Created {channel.name}")]
    elif name == "delete_channel":
        channel = await discord_client.fetch_channel(int(arguments["channel_id"]))
        await channel.delete()
        return [TextContent(type="text", text="Channel deleted.")]
    elif name == "add_reaction":
        channel = await discord_client.fetch_channel(int(arguments["channel_id"]))
        message = await channel.fetch_message(int(arguments["message_id"]))
        await message.add_reaction(arguments["emoji"])
        return [TextContent(type="text", text="Reaction added.")]
    elif name == "list_servers":
        servers = [f\"{g.name} ({g.id})\" for g in discord_client.guilds]
        return [TextContent(type="text", text="\\n".join(servers))]
    elif name == "list_roles":
        guild_id = arguments["server_id"]
        headers = {"Authorization": f"Bot {DISCORD_TOKEN}"}
        async with aiohttp.ClientSession() as session:
            async with session.get(f"https://discord.com/api/v10/guilds/{guild_id}/roles", headers=headers) as resp:
                if resp.status != 200:
                    error_text = await resp.text()
                    return [TextContent(type="text", text=f"Failed to fetch roles: {error_text}")]
                roles_data = await resp.json()
        
        PERMISSIONS = {
            1 << 0: "Create Instant Invite", 1 << 1: "Kick Members", 1 << 2: "Ban Members",
            1 << 3: "Administrator", 1 << 4: "Manage Channels", 1 << 5: "Manage Guild",
            1 << 6: "Add Reactions", 1 << 7: "View Audit Log", 1 << 8: "Priority Speaker",
            1 << 9: "Stream", 1 << 10: "View Channel", 1 << 11: "Send Messages",
            1 << 12: "Send TTS Messages", 1 << 13: "Manage Messages", 1 << 14: "Embed Links",
            1 << 15: "Attach Files", 1 << 16: "Read Message History",
            1 << 17: "Mention @everyone, @here, and All Roles", 1 << 18: "Use External Emojis",
            1 << 19: "View Guild Insights", 1 << 20: "Connect", 1 << 21: "Speak",
            1 << 22: "Mute Members", 1 << 23: "Deafen Members", 1 << 24: "Move Members",
            1 << 25: "Use VAD", 1 << 26: "Change Nickname", 1 << 27: "Manage Nicknames",
            1 << 28: "Manage Roles", 1 << 29: "Manage Webhooks", 1 << 30: "Manage Emojis and Stickers",
            1 << 31: "Use Application Commands", 1 << 32: "Request to Speak", 1 << 33: "Manage Events",
            1 << 34: "Manage Threads", 1 << 35: "Create Public Threads", 1 << 36: "Create Private Threads",
            1 << 37: "Use External Stickers", 1 << 38: "Send Messages in Threads",
            1 << 39: "Use Embedded Activities", 1 << 40: "Moderate Members",
            1 << 41: "View Creator Monitization Insights", 1 << 42: "Use Soundboard",
            1 << 43: "Use External Sounds", 1 << 44: "Send Voice Messages"
        }

        def resolve_perms(mask):
            mask = int(mask)
            return [name for bit, name in PERMISSIONS.items() if mask & bit]

        formatted_roles = []
        for r in roles_data:
            resolved = resolve_perms(r['permissions'])
            role_info = {
                "id": r['id'],
                "name": r['name'],
                "color": r['color'],
                "position": r['position'],
                "permissions_raw": r['permissions'],
                "permissions_resolved": resolved
            }
            formatted_roles.append(json.dumps(role_info, indent=2))
        
        return [TextContent(type="text", text="\\n---\\n".join(formatted_roles))]
    raise ValueError(f"Unknown tool: {name}")

async def main():
    asyncio.create_task(bot.start(DISCORD_TOKEN))
    port = os.getenv("PORT")
    if port:
        from mcp.server.sse import SseServerTransport
        transport = SseServerTransport("/messages")
        async def handle_sse(request):
            async with transport.connect_sse(request.scope, request.receive, request._send) as (read_stream, write_stream):
                await app.run(read_stream, write_stream, app.create_initialization_options())
        async def handle_messages(request):
            await transport.handle_post_message(request.scope, request.receive, request._send)
        
        middleware = [
            Middleware(AuthMiddleware)
        ]
        
        starlette_app = Starlette(debug=True, routes=[
            Route("/sse", endpoint=handle_sse),
            Route("/messages", endpoint=handle_messages, methods=["POST"]),
        ], middleware=middleware)
        
        import uvicorn
        config = uvicorn.Config(starlette_app, host="0.0.0.0", port=int(port))
        server = uvicorn.Server(config)
        await server.serve()
    else:
        async with stdio_server() as (read_stream, write_stream):
            await app.run(read_stream, write_stream, app.create_initialization_options())

if __name__ == "__main__":
    asyncio.run(main())
