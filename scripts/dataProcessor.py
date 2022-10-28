import MySQLdb as mdb  # type: ignore
from glpFetcher import GLPDataFetcher  # type: ignore
from priceFetcher import PriceFetcher
from metamaskInfoFetcher import MetamaskInfoFetcher
from binanceAccountFetcher import BinanceAccountInfo
from util.binancePairsEnumType import BinancePairsEnumType
import datetime
import time
from configparser import ConfigParser
from dotenv import load_dotenv
import os
import statistics
from typing import Dict, Union, Tuple, Optional, Any
from web3.types import ChecksumAddress, Address, ENS
from ccxt.base.errors import BadSymbol
import asyncio


class BalanceProcessor:

    def __init__(self, infura_api_key: Optional[str] = os.getenv('INFURA_API_KEY'),
                 binance_api_key: Optional[str] = os.getenv('BINANCE_API_KEY'),
                 binance_secret_key: Optional[str] = os.getenv('BINANCE_SECRET_KEY'),
                 wallet_adr: Union[ChecksumAddress, ENS, Address, Optional[str]] = os.getenv('WALLET_ADDRESS'),
                 gmx_index_assets: Tuple[str, ...] = ('WBTC', 'WETH', 'LINK', 'UNI', 'FRAX', 'USDT', 'USDC', 'DAI')
                 ):

        config = ConfigParser()
        config.read('config.ini')
        load_dotenv()
        self.wallet_adr = wallet_adr
        self.infura_api_key = infura_api_key
        self.gmx_index_assets = gmx_index_assets
        self.binance_api_key = binance_api_key
        self.binance_secret_key = binance_secret_key

        self.gmx_fetcher = GLPDataFetcher(infura_api_key=self.infura_api_key,
                                          wallet_adr=self.wallet_adr,
                                          gmx_index_assets=self.gmx_index_assets
                                          )

        self.metamask_fetcher = MetamaskInfoFetcher(infura_api_key=self.infura_api_key,
                                                    wallet_adr=self.wallet_adr)

        self.binance_fetcher = BinanceAccountInfo(binance_api_key=self.binance_api_key,
                                                  binance_secret_key=self.binance_secret_key)
        self.price_dict_binance = PriceFetcher().get_assets_price_binance(
            target_tokens=("BTC", "ETH", 'UNI', 'LINK', 'GMX', "DAI", "USDC", "USDT", 'BUSD'))
        self.price_dict_binance = PriceFetcher().get_assets_price_binance()
        self.price_dict_coingecko = PriceFetcher().get_assets_price_coingecko()
        self.price_dict_gmx = PriceFetcher().get_assets_price_gmx(infura_api_key=self.infura_api_key)
        self.binance_summary = self.get_binance_assets_summary()
        self.metamask_summary = self.get_metamask_assets_summary()
        self.gmx_summary = self.get_gmx_assets_summary()

    def get_total_notional_value_balance(self) -> Dict[str, float]:
        gmx_total_value: float = sum(self.gmx_summary['notional'].values())
        binance_total_value: float = sum(self.binance_summary['hedge']['notional'].values())
        metamask_total_value: float = sum(self.metamask_summary['notional'].values())

        return {'Binance': binance_total_value, 'GMX': gmx_total_value, 'Metamask': metamask_total_value}

    def get_binance_wallet_balances(self) -> Dict[str, Dict]:
        amount_dict: Dict[Any, float] = self.binance_summary['amount']
        wallet_dict: Dict[str, float] = dict()
        for token in amount_dict.keys():
            if token not in ['USDT', 'BUSD']:
                if amount_dict[token] != 0:
                    raise BadSymbol('Binance Futures wallet has non-stable assets')
            else:
                wallet_dict[token] = 1 * amount_dict[token]

        return {'notional': wallet_dict, 'amount': amount_dict}

    def get_margin_ratio(self):
        return self.binance_fetcher.get_total_margin_ratio()

    def _get_total_pnl(self):
        hedge_dict: Dict[str, float] = self.binance_summary['hedge']
        total_pnl = 0

        for token in hedge_dict:
            total_pnl += hedge_dict[token]['unrealizedProfit']

        return total_pnl

    def _get_gmx_assets_amount(self):
        return self.gmx_fetcher.get_assets_amounts_summary()

    def get_gmx_assets_summary(self):
        amount_dict: Dict = self._get_gmx_assets_amount()
        notional_dict: Dict = {'GLP': self.gmx_fetcher.get_balance(), 'esGMX': amount_dict['esGMX'] * 0,
                               'GMX': amount_dict['GMX'] * self.price_dict_binance['GMX'],
                               'WBTC': amount_dict['WBTC'] * self.price_dict_gmx['WBTC'],
                               'WETH': amount_dict['WETH'] * self.price_dict_gmx['WETH'],
                               'LINK': amount_dict['LINK'] * self.price_dict_gmx['LINK'],
                               'UNI': amount_dict['UNI'] * self.price_dict_gmx['UNI'],
                               "FRAX": amount_dict['FRAX'] * self.price_dict_gmx['FRAX'],
                               'DAI': amount_dict['DAI'] * self.price_dict_gmx['DAI'],
                               'USDT': amount_dict['USDT'] * self.price_dict_gmx['USDT'],
                               'USDC': amount_dict['USDC'] * self.price_dict_gmx['USDC']}

        return {'notional': notional_dict, 'amount': amount_dict}

    def _get_metamask_assets_amount(self):
        return self.metamask_fetcher.get_balance_amount()

    def get_metamask_assets_summary(self):
        amount_dict: Dict = self._get_metamask_assets_amount()
        price_dict_binance: Dict[str, float] = self.price_dict_binance
        price_dict_coingecko: Dict[str, float] = self.price_dict_coingecko
        price_dict_gmx: Dict[str, float] = self.price_dict_gmx
        notional_dict: Dict = {}

        # For GMX price, will take the mid from Binance and Coingecko
        notional_dict['GMX'] = amount_dict['GMX'] * (price_dict_coingecko['GMX'] + price_dict_binance['GMX']) / 2

        # For esGMX, since there is no instant liquidity without vesting, so the market value would be considered 0
        notional_dict['esGMX'] = amount_dict['esGMX'] * 0

        # For Frax price, will take the lower one from GMX protocol and Coingecko
        notional_dict['FRAX'] = amount_dict['FRAX'] * min(price_dict_gmx['FRAX'], price_dict_coingecko['FRAX'])

        # For WBTC, WETH, though these are different from BTC and ETH, but unless there is hack to Arbitrum Cross Chain.
        # It should be alright to use BTC and ETH as proxies.
        notional_dict['WBTC'] = statistics.mean([price_dict_binance['BTC'],
                                                 price_dict_gmx['WBTC'],
                                                 price_dict_coingecko['WBTC']]) * amount_dict['WBTC']

        notional_dict['ETH'] = statistics.mean([price_dict_binance['ETH'],
                                                 price_dict_gmx['WETH'],
                                                 price_dict_coingecko['WETH']]) * amount_dict['ETH']
        # Since USDT is a quote currency in Binance, use mean price from coingecko and GMX.

        notional_dict['USDT'] = statistics.mean([price_dict_gmx['USDT'],
                                                 price_dict_coingecko['USDT']]) * amount_dict['USDT']
        # For the others , will take the middle price from sources
        for symbol in self.gmx_fetcher.gmx_index_assets:
            if symbol not in ['GMX', 'esGMX', 'FRAX', 'WBTC', 'WETH', 'USDT']:
                notional_dict[symbol] = statistics.mean([price_dict_binance[symbol],
                                                         price_dict_gmx[symbol],
                                                         price_dict_coingecko[symbol]
                                                         ]) * amount_dict[symbol]

        return {'notional': notional_dict, 'amount': amount_dict}

    def get_binance_assets_summary(self):
        return self.binance_fetcher.get_summary()

    def get_claimable_info(self):
        return self.gmx_fetcher.get_claimable_info()


if __name__ == '__main__':
    start_time = time.time()
    test = BalanceProcessor()
    phase1 = time.time()
    print(f'Initialization time is: {phase1 - start_time}')
    print(test.get_gmx_assets_summary())
