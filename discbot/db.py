from peewee import * 
from dotenv import dotenv_values

config = dotenv_values('.env')
db = SqliteDatabase(config['database'])

class BaseModel(Model):
    class Meta:
        database = db

class User(BaseModel):
    userid = CharField(primary_key=True)
    name = CharField()
    points = FloatField('points > -1')

class Investments(BaseModel):
    investmentid = AutoField(primary_key=True)
    investment_name = CharField(unique=True)
    alpha = FloatField()
    beta = FloatField()
    bias = FloatField()
    value = FloatField()
    dividend_rate = FloatField()

class Holdings(BaseModel):
    userid = ForeignKeyField(User, backref='holdings')
    investmentid = ForeignKeyField(Investments, backref='trades')
    amount = IntegerField('amount > -1')

db.create_tables([User, Investments, Holdings])

class DataBaseInteractor:
    def get_points(self, id):
        try:
            user = User.get(User.userid == id)
            return user.points
        except User.DoesNotExist:
            return 0
    
    def add_points(self, id, name, numpoints):
        try:
            user = User.get(User.userid == id)
            user.points += numpoints
            user.save()
        except User.DoesNotExist:
            user = User.create(userid=id, name=name, points=numpoints)
        return user.points

    def remove_points(self, id, name, numpoints):
        try:
            user = User.get(User.userid == id)
            user.points = max(user.points - numpoints, 0)
            user.save()
        except User.DoesNotExist:
            user = User.create(userid=id, name=name, points=0)
        return user.points

    def add_investment_if_not_present(self, investment_name: str, dividend_rate: float, start_val: float, beta: list):
        try:
            Investments.get(Investments.investment_name == investment_name)
        except Investments.DoesNotExist:
            alpha, beta, bias = beta
            Investments.create(investment_name=investment_name, dividend_rate=max(0, dividend_rate), 
                               value=max(1, start_val), alpha=alpha, beta=beta, bias=bias)

    def buy_stock(self, userid, stockid, amount) -> int:
        amount = max(amount, 0)
        try:
            user = User.get(User.userid == userid)
            stock = Investments.get(Investments.investmentid == stockid)
            if user.points < stock.value * amount:
                return 3
            
            user.points -= stock.value * amount
            trade, created = Holdings.get_or_create(userid=userid, investmentid=stockid)
            if created:
                trade.amount = 0
            trade.amount += amount
            trade.save()
            user.save()
            return 0
        except User.DoesNotExist:
            return 1
        except Investments.DoesNotExist:
            return 2
        
    def get_investments_by_user(self, userid):
        investments = (Investments.select(Investments, Holdings)
                       .join(Holdings)
                       .where(Holdings.userid == userid))
        return investments
    
    def sell_stock(self, userid, investmentid, amount):
        try:
            user = User.get(User.userid == userid)
            value = Investments.get(Investments.investmentid == investmentid).value
            trade = Holdings.get(Holdings.userid == userid, Holdings.investmentid == investmentid)
            
            selling = min(amount, trade.amount)
            user.points += value * selling
            trade.amount -= selling 
            user.save()
            trade.save()
            return 0
        except User.DoesNotExist:
            return 1
        except Investments.DoesNotExist:
            return 2
        except Holdings.DoesNotExist:
            return 3
    
    def get_all_investments(self):
        investments = Investments.select()
        return investments

    def all_users(self):
        users = User.select().order_by(User.points.desc())
        return users


