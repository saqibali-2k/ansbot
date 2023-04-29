import discord
from discord.ext import commands, tasks
import json
from dotenv import dotenv_values
from investments import invest
import db
import datetime

TIMES = [
    datetime.time(hour=13, minute=30, tzinfo=datetime.timezone.utc),
    datetime.time(hour=16, minute=0, tzinfo=datetime.timezone.utc),
    datetime.time(hour=18, minute=30, tzinfo=datetime.timezone.utc),
    datetime.time(hour=21, minute=0, tzinfo=datetime.timezone.utc)
]

config = dotenv_values('.env')
admins = [int(id) for id in json.loads(config['admin'])]

# Set up the bot client
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix=config['prefix'], intents=intents)
dbtool = db.DataBaseInteractor()

async def authenticate(ctx):
    if ctx.author.id not in admins:
        await ctx.send(f"{ctx.author.nick or ctx.author.name} is not an admin.")
        return False
    return True

async def show_points(ctx, name, val):
    await ctx.send(f"User: {name}, Points: {val:.2f}")


@bot.command()
async def awardall(ctx, points: int):
    try:
        if await authenticate(ctx):
            for user in dbtool.all_users():
                dbtool.add_points(user.userid, user.name, points)
        await ctx.message.add_reaction('✅')
    except:
        await ctx.message.add_reaction('❌')

@bot.command()
async def award(ctx, user: discord.Member, points: int):
    if await authenticate(ctx):
        name = user.nick or user.name
        val = dbtool.add_points(user.id, name, points)
        await show_points(ctx, name, val)

@bot.command()
async def punish(ctx, user: discord.Member, points: int):
    if await authenticate(ctx):
        name = user.nick or user.name
        newval = dbtool.remove_points(user.id, name, points)
        await show_points(ctx, name, newval)

@bot.command()
async def points(ctx: commands.Context):
    newval = dbtool.get_points(ctx.author.id)
    name = ctx.author.nick or ctx.author.name
    await show_points(ctx, name, newval)

@bot.command()
async def send(ctx: commands.Context, user: discord.Member, points: int):
    to_user  = user.id
    from_user = ctx.author.id
    if dbtool.get_points(from_user) < points:
        await ctx.message.add_reaction('❌')
        await ctx.message.add_reaction('💰')
    else:
        dbtool.remove_points(from_user, ctx.author.nick or ctx.author.name, points)
        dbtool.add_points(to_user, user.nick or user.name, points)
        await ctx.message.add_reaction('✅')

@bot.command()
async def market(ctx):
    stocks = dbtool.get_all_investments()
    message = "Stocks: \n"
    for stock in stocks:
        message += f"{stock.investmentid}: {stock.investment_name} @ {stock.value:.2f} ANS ({stock.dividend_rate * 100}%) \n"
    await ctx.send(message)

@tasks.loop(time=TIMES)
async def update_stocks():
    await payouts()
    channel = bot.get_channel(int(config['channelid']))
    logs = invest.update_stocks(dbtool)
    message = "Updates: \n"
    for stock, change in logs.items():
        prev, now = change
        message += f"{stock}: {prev:.2f} -> {now:.2f} \n"
    await channel.send(message)

@bot.command()
async def man_update(ctx: commands.Context):
    if await authenticate(ctx):
        await payouts()
        channel = bot.get_channel(int(config['channelid']))
        logs = invest.update_stocks(dbtool)
        message = "Updates: \n"
        for stock, change in logs.items():
            prev, now = change
            message += f"{stock}: {prev:.2f} -> {now:.2f} \n"
    await channel.send(message)

async def payouts():
    channel = bot.get_channel(int(config['channelid']))
    invest.assign_payouts(dbtool)
    await channel.send("Payouts complete!")

@bot.command()
async def buy(ctx: commands.Context, investmentid: int, numShares: float):
    ret = dbtool.buy_stock(ctx.author.id, investmentid, numShares)
    if ret == 0:
        await ctx.message.add_reaction('✅')
    elif ret == 1:
        # person not in db
        await ctx.message.add_reaction('❌')
        await ctx.message.add_reaction('👶')
    elif ret == 2:
        # stock not found
        await ctx.message.add_reaction('❌')
        await ctx.message.add_reaction('❔')
    elif ret == 3:
        await ctx.message.add_reaction('❌')
        await ctx.message.add_reaction('💰')

@bot.command()
async def holdings(ctx, user: discord.Member=None):
    if user is None:
        user = ctx.author 
    investments = dbtool.get_investments_by_user(user.id)
    message = f"{user.mention}'s stocks: \n"
    for stock in investments:
        if stock.holdings.amount == 0:
            continue
        message += f"[{stock.investmentid}] {stock.investment_name}: {stock.holdings.amount:.3f} ({stock.holdings.amount * stock.value:.2f}) \n"
    await ctx.send(message)

@bot.command()
async def sell(ctx, investmentid: int, amount: float):
    if amount <= 0:
        return
    ret = dbtool.sell_stock(ctx.author.id, investmentid, amount)
    if ret == 0:
        await ctx.message.add_reaction('✅')
    elif ret == 1:
        await ctx.message.add_reaction('❌')
        await ctx.message.add_reaction('👶')
    elif ret == 2:
        await ctx.message.add_reaction('❌')
        await ctx.message.add_reaction('❔')
    elif ret == 3:
        await ctx.message.add_reaction('❌')
        await ctx.send("You don't own more of this stock.")

@bot.command()
async def leaderboard(ctx):
    message = "Leaderboard: \n"
    for i, user in enumerate(dbtool.all_users()):
        message += f"[{i+1}] User: {user.name}, Points: {user.points:.2f}\n"

    await ctx.send(message)

@bot.listen()
async def on_ready():
    update_stocks.start()

# Run the bot
invest.set_investments(dbtool, config['investments'])
bot.run(config['token'])