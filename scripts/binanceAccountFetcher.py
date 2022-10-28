import ccxt
from typing import Dict, Optional, Iterable, List, Union
import os
from dotenv import load_dotenv
from util.binancePairsEnumType import BinancePairsEnumType
load_dotenv()
import time


class BinanceAccountInfo:

    def __init__(self, binance_api_key: Optional[str] = os.getenv('BINANCE_API_KEY'),
                 binance_secret_key: Optional[str] = os.getenv('BINANCE_SECRET_KEY')):
        self.api_key = binance_api_key
        self.secret_key = binance_secret_key
        self._conn = ccxt.binance({
            'apiKey': self.api_key,
            'secret': self.secret_key,
            'options': {
                'defaultType': 'future'
            }
        })

    def get_balance_amount(self) -> Dict[str, float]:
        balance = self._conn.fetch_balance()
        amount_balance: Dict = {}

        for token in balance['info']['assets']:
            amount_balance[token['asset']] = float(token['walletBalance'])

        return amount_balance

    def get_total_margin_ratio(self) -> float:

        stable_list: List = ['USDT', 'BUSD']

        total_maintenance_margin: float = 0
        total_margin: float = 0

        balance = self._conn.fetch_balance()

        for token in balance['info']['assets']:
            if token['asset'] in stable_list:
                total_margin += float(token['marginBalance'])
                total_maintenance_margin += float(token['maintMargin'])

        return total_maintenance_margin / total_margin

    def get_hedge_info(self, pairs: Iterable[str] = BinancePairsEnumType._member_names_) -> Dict[str, float]:
        balance = self._conn.fetch_positions()
        info_dict: Dict = {'notional': {}, 'unrealizedProfit': {}, 'positionAmt':{},
                           'base': {}, 'quote': {}, 'funding_rate': {}, 'leverage': {}}
        for pair in pairs:
            for position in balance:
                if pair == position['info']['symbol']:
                    info_dict['notional'][pair] = float(position['info']['notional'])
                    info_dict['unrealizedProfit'][pair] = float(position['info']['unRealizedProfit'])
                    info_dict['positionAmt'][pair] = float(position['info']['positionAmt'])
                    info_dict['base'][pair] = position['info']['symbol'][:-4]
                    info_dict['quote'][pair] = position['info']['symbol'][-4:]
                    info_dict['funding_rate'][pair] = self.get_funding_rate(pair)
                    info_dict['leverage'][pair] = 0

                    if float(position['info']['positionAmt']) != 0:
                        info_dict['leverage'][pair] = float(position['leverage'])

        return info_dict

    @classmethod
    def get_funding_rates(cls, pairs: Iterable[str] = BinancePairsEnumType._member_names_) -> Dict[str, float]:

        binanceusdm = ccxt.binanceusdm()
        funding_dict: Dict = {}

        for pair in pairs:
            funding_dict[pair] = float(binanceusdm.fetchFundingRate(pair)['info']['lastFundingRate'])

        return funding_dict

    @classmethod
    def get_funding_rate(cls, pair: str) -> float:
        binanceusdm = ccxt.binanceusdm()
        return float(binanceusdm.fetchFundingRate(pair)['info']['lastFundingRate'])

    def get_summary(self) -> Dict[str, Union[Dict, float]]:
        return {'hedge': self.get_hedge_info(),
                'amount': self.get_balance_amount(),
                'margin_ratio': self.get_total_margin_ratio()}


if __name__ == '__main__':
    start_time = time.time()
    test = BinanceAccountInfo()
    print(test.get_summary())
    print(test.get_hedge_info())
    # print(test.get_total_margin_ratio())
    print(f'process time is: {time.time() - start_time}')