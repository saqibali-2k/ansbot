import numpy as np
import json
from db import *

def set_investments(dbtool: DataBaseInteractor, path: str):
    with open(path) as defintions:
        investments = json.load(defintions)
        for investment in investments:
            dbtool.add_investment_if_not_present(investment['name'], investment['dividend'], 
                                                 investment['start'],  investment['beta'])

def update_stocks(dbtool: DataBaseInteractor):
    investments = dbtool.get_all_investments()
    logs = {}
    for stock in investments:
        prev_val = stock.value
        stock.value *= np.random.beta(stock.alpha, stock.beta) + stock.bias
        stock.value = max(stock.value, 1)
        new_val = stock.value
        stock.save()
        logs[stock.investment_name] = [prev_val, new_val]
    return logs

def assign_payouts(dbtool: DataBaseInteractor):
    investments = dbtool.get_all_investments()
    for stock in investments:
        trades = stock.trades
        for trade in trades:
            user = User.get(User.userid == trade.userid)
            user.points += stock.value * stock.dividend_rate * trade.amount 
            user.save()