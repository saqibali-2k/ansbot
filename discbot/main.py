import discord
from discord.ext import commands, tasks
import json
from dotenv import dotenv_values
from investments import invest
import db

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
async def points(ctx):
    newval = dbtool.get_points(ctx.author.id)
    name = ctx.author.nick or ctx.author.name
    await show_points(ctx, name, newval)

@bot.command()
async def market(ctx):
    stocks = dbtool.get_all_investments()
    message = "Stocks: \n"
    for stock in stocks:
        message += f"{stock.investmentid}: {stock.investment_name} @ {stock.value:.2f} ANS ({stock.dividend_rate}) \n"
    await ctx.send(message)

@tasks.loop(hours=6)
async def update_stocks():
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
async def buy(ctx, investmentid: int, numShares: int):
    ret = dbtool.buy_stock(ctx.author.id, investmentid, numShares)
    if ret == 0:
        await ctx.send("Transation complete.")
    elif ret == 1:
        await ctx.send("You are not in the database.")
    elif ret == 2:
        await ctx.send("Uknown ID for stock.")
    elif ret == 3:
        await ctx.send("Insufficient funds.")

@bot.command()
async def myholdings(ctx):
    investments = dbtool.get_investments_by_user(ctx.author.id)
    message = f"{ctx.author.mention}'s stocks: \n"
    for stock in investments:
        if stock.holdings.amount == 0:
            continue
        message += f"[{stock.investmentid}] {stock.investment_name}: {stock.holdings.amount:.3f} ({stock.holdings.amount * stock.value:.2f}) \n"
    await ctx.send(message)

@bot.command()
async def sell(ctx, investmentid: int, amount: int):
    if amount <= 0:
        return
    ret = dbtool.sell_stock(ctx.author.id, investmentid, amount)
    if ret == 0:
        await ctx.send("Transaction complete.")
    elif ret == 1:
        await ctx.send("You are not in the database.")
    elif ret == 2:
        await ctx.send("Incorrect investment ID.")
    elif ret == 3:
        await ctx.send("You don't own this stock.")

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