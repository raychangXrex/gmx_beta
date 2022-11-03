from web3 import HTTPProvider, Web3
from configparser import ConfigParser
import json
import requests
from requests.exceptions import ConnectionError
import ccxt
from typing import List, Dict, Iterable, Any, Optional
from dotenv import load_dotenv
import os
from util.tokensInfoEnumType import TokenAddressEnumType
from util.contractInfoEnumType import ContractAddressEnumType, ContractAbiEnumType
from web3.types import ChecksumAddress
import time
from util.binancePairsEnumType import BinancePairsEnumType
import ccxt

config = ConfigParser()
config.read('config.ini')
load_dotenv()


class PriceFetcher:
    def __init__(self):
        """
        Just a collection of price feed
        """

        pass

    @classmethod
    def get_assets_price_coingecko(cls, chain_id='arbitrum-one', vs_currency='usd',
                                   target_tokens: Iterable[str] =
                                   ('WBTC', 'WETH', 'LINK', 'UNI', 'FRAX', 'USDT', 'USDC', 'DAI', 'GMX')) -> Dict:

        url_root: str = 'https://api.coingecko.com/api/v3/simple/token_price/'
        target_contract: Any = ''

        for token in target_tokens:
            target_contract = target_contract + TokenAddressEnumType[token].value + ','

        target_contract = target_contract[:-1]
        url = url_root + f'{chain_id}?contract_addresses={target_contract}&vs_currencies={vs_currency}'

        res = requests.get(url)

        if res.status_code != 200:
            raise ConnectionError(json.loads(res.text)["status"]['error_message'])

        price_dict = json.loads(res.text)

        price_dict_return = {}
        # mapping to readable dictionary
        for token in target_tokens:
            price_dict_return[token] = price_dict[TokenAddressEnumType[token].value.lower()]['usd']

        return price_dict_return

    @classmethod
    def get_asset_price_coinmarket(cls,
                                   api_key: str = os.getenv("COINMARKETCAP_API_KEY"),  # type: ignore
                                   target_tokens: Iterable[str] = ("BTC", "ETH", 'UNI', 'LINK')) -> Dict[str, float]:

        url: str = 'https://pro-api.coinmarketcap.com/v2/cryptocurrency/quotes/latest'
        query_string: str = ''

        for symbol in target_tokens:
            query_string += symbol + ','

        query_string = query_string[:-1]
        parameters: Dict = {'symbol': query_string,
                            'convert': 'USD'
                            }

        headers: Dict = {
            'Accepts': 'application/json',
            'X-CMC_PRO_API_KEY': api_key,
            'aux': None
        }

        session = requests.session()
        session.headers.update(headers)

        res = session.get(url, params=parameters)
        data = json.loads(res.text)

        dict_return: Dict = {}

        for symbol in target_tokens:
            dict_return[symbol] = data['data'][symbol][0]['quote']['USD']['price']

        return dict_return

    @classmethod
    def get_assets_price_binance(cls,
                                 target_tokens: Iterable[str] =
                                 ("BTC", "ETH", 'UNI', 'LINK', 'GMX', "DAI", "USDC", "USDT")) \
            -> Dict[str, float]:
        """
        Use the close price of 1m, FRAX pairs is not available on Binance, account unit is USDT
        """

        binanceusdm = ccxt.binance()
        price_dict: Dict[str, float] = {}

        # Fetch the last close price from 1m OHLCV
        for token in target_tokens:
            if token != 'USDT':
                symbol = token + "USDT"
                price_dict[token] = binanceusdm.fetch_ohlcvc(symbol)[-1][-3]
            else:
                price_dict[token] = 1

        return price_dict

    @classmethod
    def get_assets_price_gmx(cls, infura_api_key: Optional[str] = os.getenv('INFURA_API_KEY')) -> Dict[str, float]:
        infura_api_url: str = f"https://arbitrum-mainnet.infura.io/v3/{infura_api_key}"
        gmx_index_assets: Iterable[str] = ('WBTC', 'WETH', 'LINK', 'UNI', 'FRAX', 'USDT', 'USDC', 'DAI')
        vault_adr: ChecksumAddress = ContractAddressEnumType.vault.value
        weth_adr: ChecksumAddress = TokenAddressEnumType.WETH.value
        usdg_amount: int = 0  # only used to call vault.getRedemptionAmount(token, _usdgAmount), in unit 10**30

        # GMX index address address
        token_adr: List = [TokenAddressEnumType[token].value for token in gmx_index_assets]
        conn = Web3(HTTPProvider(infura_api_url))
        reader_contract = conn.eth.contract(address=ContractAddressEnumType.Reader.value,
                                            abi=ContractAbiEnumType.Reader.value)
        response = reader_contract.functions.getVaultTokenInfoV2(vault_adr, weth_adr, usdg_amount, token_adr).call()
        info_dict: Dict[str, float] = {}
        props_length: int = 14

        for prop, symbol in enumerate(gmx_index_assets):
            price_not_maximised = -1
            for counter in range(props_length):
                if counter % 14 == 12:
                    price_not_maximised = response[prop * 14 + 12]/10**30

            info_dict[symbol] = price_not_maximised

        return info_dict

    @classmethod
    def get_funding_rate_binance(cls, pairs: Iterable[str] = BinancePairsEnumType._member_names_) -> Dict[str, float]:

        binanceusdm = ccxt.binanceusdm()
        funding_dict: Dict = {}

        for pair in pairs:
            funding_dict[pair] = float(binanceusdm.fetchFundingRate(pair)['info']['lastFundingRate'])

        return funding_dict



if __name__ == '__main__':
    start_time = time.time()
    test = PriceFetcher()
    print(test.get_assets_price_coingecko())
    print(test.get_assets_price_binance())
    print(test.get_assets_price_gmx())
    print(test.get_funding_rate_binance())
    # print(test.get_assets_price_coingecko())

    print(f'process time is: {time.time() - start_time}')
