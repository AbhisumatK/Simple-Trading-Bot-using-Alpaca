from lumibot.brokers import Alpaca
from lumibot.strategies.strategy import Strategy
from lumibot.backtesting import YahooDataBacktesting
from lumibot.traders import Trader
from datetime import datetime
from alpaca_trade_api import REST
from timedelta import Timedelta
from finbert_utils import estimate_sentiment

API_Key = 'PKJ46DSHFGMWHMTKPZ6YEO5FEP'
API_Secret = '9cuNyWcbfFVWjXaQYPD7vcPYXjKoTSwAi9KJnG1QfyYA'
Base_URL = 'https://paper-api.alpaca.markets/v2'

Alpaca_Creds = {
    'API_KEY': API_Key,
    'API_SECRET': API_Secret,
    'PAPER': True,
}

class ML_Trader(Strategy):
    def initialize(self, symbol: str = 'SPY', cash_at_risk:float = 0.5):
        self.symbol = symbol
        self.sleep_time = '24H'
        self.last_trade = None
        self.cash_at_risk = cash_at_risk
        self.api = REST(base_url=Base_URL, key_id=API_Key, secret_key=API_Secret)

    def position_sizing(self):
        cash = self.get_cash()
        last_price = self.get_last_price(self.symbol)
        quantity = round(cash * self.cash_at_risk / last_price,0)
        return cash, last_price, quantity

    def get_dates(self): 
        today = self.get_datetime()
        three_days_prior = today - Timedelta(days=3)
        return today.strftime('%Y-%m-%d'), three_days_prior.strftime('%Y-%m-%d')
    
    def get_sentiment(self): 
        today, three_days_prior = self.get_dates()
        news = self.api.get_news(symbol=self.symbol, 
                                 start=three_days_prior, 
                                 end=today) 
        news = [ev.__dict__["_raw"]["headline"] for ev in news]
        probability, sentiment = estimate_sentiment(news)
        return probability, sentiment 

    def on_trading_iteration(self):
        cash, last_price, quantity = self.position_sizing() 
        probability, sentiment = self.get_sentiment()

        if cash > last_price: 
            if sentiment == "positive" and probability > .999: 
                if self.last_trade == "sell": 
                    self.sell_all() 
                order = self.create_order(
                    self.symbol, 
                    quantity, 
                    "buy", 
                    type="bracket", 
                    take_profit_price=last_price*1.20, 
                    stop_loss_price=last_price*.95
                )
                self.submit_order(order) 
                self.last_trade = "buy"
            elif sentiment == "negative" and probability > .999: 
                if self.last_trade == "buy": 
                    self.sell_all() 
                order = self.create_order(
                    self.symbol, 
                    quantity, 
                    "sell", 
                    type="bracket", 
                    take_profit_price=last_price*.8, 
                    stop_loss_price=last_price*1.05
                )
                self.submit_order(order) 
                self.last_trade = "sell"



start_date = datetime(2024, 10, 5)
end_date = datetime(2024, 10, 9)

broker = Alpaca(Alpaca_Creds)

strategy = ML_Trader(name='mlstrat', broker=broker, parameters={'symbol': 'SPY', 'cash_at_risk': 0.5})
strategy.backtest(YahooDataBacktesting, start_date, end_date, parameters={'symbol': 'SPY', 'cash_at_risk': 0.5})