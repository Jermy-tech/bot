import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import Button, View
import aiohttp
import asyncio
import os
import webserver

os.environ['PORT'] = '8080'

token = os.environ["discordtoken"]
intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

# API endpoints
OFFSET_API_URL = "https://rbxstats.xyz/api/offsets"
SEARCH_API_URL = "https://rbxstats.xyz/api/offsets/search/"
PREFIX_API_URL = "https://rbxstats.xyz/api/offsets/prefix/"
CAMERA_API_URL = "https://rbxstats.xyz/api/offsets/camera"
LATEST_VERSION_API_URL = "https://rbxstats.xyz/api/versions/latest"
FUTURE_VERSION_API_URL = "https://rbxstats.xyz/api/versions/future"
EXPLOITS_API_URL = "https://rbxstats.xyz/api/exploits/"

# Function to fetch data with timeout
async def fetch_data(url):
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, timeout=10) as response:  # 10-second timeout
                if response.status == 200:
                    return await response.json()
                return None
        except asyncio.TimeoutError:
            return None

# Function to fetch offsets from API
async def fetch_offsets():
    return await fetch_data(OFFSET_API_URL)

# Function to search for a specific offset by name
async def search_offset(name):
    return await fetch_data(SEARCH_API_URL + name)

# Function to search for offsets by prefix
async def search_prefix(prefix):
    return await fetch_data(PREFIX_API_URL + prefix)

# Function to fetch camera offsets
async def fetch_camera_offsets():
    return await fetch_data(CAMERA_API_URL)

# View class for pagination of exploit details
class ExploitView(View):
    def __init__(self, exploits, index=0):
        super().__init__(timeout=60)  # 60 seconds timeout for inactivity
        self.exploits = exploits
        self.index = index
        self.update_buttons()

    def update_buttons(self):
        self.clear_items()
        if self.index > 0:
            back_button = Button(label="Back", style=discord.ButtonStyle.secondary, emoji="◀️")
            back_button.callback = self.go_back
            self.add_item(back_button)
        if self.index < len(self.exploits) - 1:
            next_button = Button(label="Next", style=discord.ButtonStyle.secondary, emoji="▶️")
            next_button.callback = self.go_forward
            self.add_item(next_button)

        # Add buttons for website and Discord links
        current_exploit = self.exploits[self.index]
        if "websitelink" in current_exploit and current_exploit["websitelink"]:
            website_button = Button(label="Website", url=current_exploit["websitelink"])
            self.add_item(website_button)
        if "discordlink" in current_exploit and current_exploit["discordlink"]:
            discord_button = Button(label="Discord", url=current_exploit["discordlink"])
            self.add_item(discord_button)

    async def go_back(self, interaction: discord.Interaction):
        self.index -= 1
        self.update_buttons()
        await interaction.response.edit_message(embed=self.create_embed(), view=self)

    async def go_forward(self, interaction: discord.Interaction):
        self.index += 1
        self.update_buttons()
        await interaction.response.edit_message(embed=self.create_embed(), view=self)

    def create_embed(self):
        exploit = self.exploits[self.index]
        embed = discord.Embed(
            title=exploit["title"],
            description=f"Version: `{exploit['version']}`\n"
                        f"Updated: `{exploit['updatedDate']}`\n"
                        f"Platform: `{exploit['platform']}`",
            color=discord.Color.purple()
        )
        return embed

# View class for pagination of offset search results
class OffsetView(View):
    def __init__(self, offsets, page=0, max_per_page=10):
        super().__init__(timeout=60)  # 60 seconds timeout for inactivity
        self.offsets = offsets
        self.page = page
        self.max_per_page = max_per_page
        self.update_buttons()

    def update_buttons(self):
        self.clear_items()
        if self.page > 0:
            back_button = Button(label="Back", style=discord.ButtonStyle.secondary, emoji="◀️")
            back_button.callback = self.go_back
            self.add_item(back_button)
        if (self.page + 1) * self.max_per_page < len(self.offsets):
            next_button = Button(label="Next", style=discord.ButtonStyle.secondary, emoji="▶️")
            next_button.callback = self.go_forward
            self.add_item(next_button)

    async def go_back(self, interaction: discord.Interaction):
        self.page -= 1
        self.update_buttons()
        await interaction.response.edit_message(embed=self.create_embed(), view=self)

    async def go_forward(self, interaction: discord.Interaction):
        self.page += 1
        self.update_buttons()
        await interaction.response.edit_message(embed=self.create_embed(), view=self)

    def create_embed(self):
        start = self.page * self.max_per_page
        end = start + self.max_per_page
        page_data = list(self.offsets.items())[start:end]

        embed = discord.Embed(
            title=f"Offsets - Page {self.page + 1}",
            description="Here are the offsets retrieved from the API.",
            color=discord.Color.blurple()
        )

        for key, value in page_data:
            embed.add_field(name=key, value=f"`{value}`", inline=True)

        embed.set_footer(text=f"Page {self.page + 1}/{(len(self.offsets) // self.max_per_page) + 1}")
        return embed

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}!')
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} command(s)")
    except Exception as e:
        print(e)

# /offsets command - Get a list of 10 offsets at a time
@bot.tree.command(name="offsets", description="Get a list of 10 offsets at a time")
async def offsets_command(interaction: discord.Interaction):
    await interaction.response.send_message("Loading offsets...", ephemeral=True)
    offsets = await fetch_offsets()
    if not offsets:
        await interaction.edit_original_response(content="Failed to fetch offsets.")
        return

    view = OffsetView(offsets)
    embed = view.create_embed()
    await interaction.edit_original_response(content=None, embed=embed, view=view)

# /searchoffset command - Search for a specific offset by name
@bot.tree.command(name="searchoffset", description="Search for a specific offset")
async def searchoffset(interaction: discord.Interaction, offset_name: str):
    await interaction.response.send_message(f"Searching for offset: {offset_name}...", ephemeral=True)
    result = await search_offset(offset_name)
    if not result:
        await interaction.edit_original_response(content=f"Offset `{offset_name}` not found.")
        return

    embed = discord.Embed(
        title=f"Offset: {offset_name}",
        description=f"Here is the data for `{offset_name}`.",
        color=discord.Color.green()
    )

    for key, value in result.items():
        embed.add_field(name=key, value=f"`{value}`", inline=True)

    await interaction.edit_original_response(content=None, embed=embed)

# /prefixoffset command - Search for offsets by prefix
@bot.tree.command(name="prefixoffset", description="Search for offsets by prefix")
async def prefixoffset(interaction: discord.Interaction, prefix: str):
    await interaction.response.send_message(f"Searching for offsets starting with `{prefix}`...", ephemeral=True)
    result = await search_prefix(prefix)
    if not result or len(result) == 0:
        await interaction.edit_original_response(content=f"No offsets found with prefix `{prefix}`.")
        return

    view = OffsetView(result)
    embed = view.create_embed()
    await interaction.edit_original_response(content=None, embed=embed, view=view)

# /camera command - Fetch and display camera offsets
@bot.tree.command(name="camera", description="Get all camera-related offsets")
async def camera_command(interaction: discord.Interaction):
    await interaction.response.send_message("Fetching camera offsets...", ephemeral=True)
    result = await fetch_camera_offsets()
    if isinstance(result, str) and result == "Offsets outdated, please wait for new offsets":
        await interaction.edit_original_response(content=result)
        return

    if not result:
        await interaction.edit_original_response(content="Failed to fetch camera offsets.")
        return

    embed = discord.Embed(
        title="Camera Offsets",
        description="Here are the camera-related offsets retrieved from the API:",
        color=discord.Color.purple()
    )

    for key, value in result.items():
        embed.add_field(name=key, value=f"`{value}`", inline=False)

    await interaction.edit_original_response(content=None, embed=embed)

# Exploit command handler with pagination
async def handle_exploit_command(interaction: discord.Interaction, filter_type: str):
    await interaction.response.send_message(f"Fetching exploits for {filter_type}...", ephemeral=True)
    exploits = await fetch_data(EXPLOITS_API_URL)

    if not exploits:
        await interaction.edit_original_response(content="Failed to fetch exploits.")
        return

    filtered_exploits = [
        exploit for exploit in exploits
        if (filter_type == "windows" and exploit["platform"] == "Windows") or
           (filter_type == "mac" and exploit["platform"] == "Mac") or
           (filter_type == "detected" and exploit["detected"]) or
           (filter_type == "undetected" and not exploit["detected"]) or
           (filter_type == "free" and exploit["free"]) or
           (filter_type == "paid" and not exploit["free"]) or
           (filter_type == "indev" and exploit["beta"])
    ]

    if not filtered_exploits:
        await interaction.edit_original_response(content=f"No exploits found for {filter_type}.")
        return

    view = ExploitView(filtered_exploits)
    await interaction.edit_original_response(embed=view.create_embed(), view=view)

# Command for Windows specific exploits
@bot.tree.command(name="windows", description="Get Windows specific exploits")
async def windows_command(interaction: discord.Interaction):
    await handle_exploit_command(interaction, "windows")

# Command for Mac specific exploits
@bot.tree.command(name="mac", description="Get Mac specific exploits")
async def mac_command(interaction: discord.Interaction):
    await handle_exploit_command(interaction, "mac")

# Command for detected exploits
@bot.tree.command(name="detected", description="Get detected exploits")
async def detected_command(interaction: discord.Interaction):
    await handle_exploit_command(interaction, "detected")

# Command for undetected exploits
@bot.tree.command(name="undetected", description="Get undetected exploits")
async def undetected_command(interaction: discord.Interaction):
    await handle_exploit_command(interaction, "undetected")

# Command for free exploits
@bot.tree.command(name="free", description="Get free exploits")
async def free_command(interaction: discord.Interaction):
    await handle_exploit_command(interaction, "free")

# Command for paid exploits
@bot.tree.command(name="paid", description="Get paid exploits")
async def paid_command(interaction: discord.Interaction):
    await handle_exploit_command(interaction, "paid")

# Command for in-development exploits
@bot.tree.command(name="indev", description="Get in-development exploits")
async def indev_command(interaction: discord.Interaction):
    await handle_exploit_command(interaction, "indev")

# Command to get the count of all exploits
@bot.tree.command(name="count", description="Get the count of all exploits")
async def count_command(interaction: discord.Interaction):
    await interaction.response.send_message("Fetching exploit count...", ephemeral=True)
    exploits = await fetch_data(EXPLOITS_API_URL)

    if not exploits:
        await interaction.edit_original_response(content="Failed to fetch exploits.")
        return

    count = len(exploits)
    await interaction.edit_original_response(content=f"Total exploits: {count}")

# Command to fetch the latest Roblox version
@bot.tree.command(name="version", description="Get the latest Roblox version")
async def version_command(interaction: discord.Interaction):
    await interaction.response.send_message("Fetching latest version...", ephemeral=True)
    latest_version = await fetch_data(LATEST_VERSION_API_URL)

    if not latest_version:
        await interaction.edit_original_response(content="Failed to fetch latest version.")
        return

    embed = discord.Embed(
        title="Latest Roblox Version",
        color=discord.Color.blue()
    )
    embed.add_field(name="Windows", value=f"`{latest_version['Windows']}`\nDate: `{latest_version['WindowsDate']}`", inline=False)
    embed.add_field(name="Mac", value=f"`{latest_version['Mac']}`\nDate: `{latest_version['MacDate']}`", inline=False)
    
    await interaction.edit_original_response(embed=embed)

# Command to fetch the future Roblox version
@bot.tree.command(name="futureversion", description="Get the future Roblox version")
async def future_version_command(interaction: discord.Interaction):
    await interaction.response.send_message("Fetching future version...", ephemeral=True)
    future_version = await fetch_data(FUTURE_VERSION_API_URL)

    if not future_version:
        await interaction.edit_original_response(content="Failed to fetch future version.")
        return

    embed = discord.Embed(
        title="Future Roblox Version",
        color=discord.Color.green()
    )
    embed.add_field(name="Windows", value=f"`{future_version['Windows']}`\nDate: `{future_version['WindowsDate']}`", inline=False)
    embed.add_field(name="Mac", value=f"`{future_version['Mac']}`\nDate: `{future_version['MacDate']}`", inline=False)
    
    await interaction.edit_original_response(embed=embed)

webserver.keep_alive()

# Run the bot with your token
bot.run(token)
