from web3 import HTTPProvider, Web3
from typing import Iterable, Dict, Union, Optional
from util.tokensInfoEnumType import TokenAddressEnumType, TokenDecimalsEnumType, TokenAbiEnumType
from web3.types import ChecksumAddress, Address, ENS
import os
from dotenv import load_dotenv
import time

load_dotenv()


class MetamaskInfoFetcher:
    def __init__(self,
                 infura_api_key: Optional[str] = os.getenv('INFURA_API_KEY'),  # type: ignore
                 wallet_adr: Union[ChecksumAddress, ENS, Address, Optional[str]] = os.getenv('WALLET_ADDRESS')):

        infura_api_url: str = 'https://arbitrum-mainnet.infura.io/v3/'
        infura_api_url = infura_api_url + infura_api_key  # type: ignore
        self.conn = Web3(HTTPProvider(infura_api_url))
        self.wallet_adr = wallet_adr

    def get_balance_amount(self, token_iterable: Iterable[str] = ('WBTC', 'WETH', 'ETH', 'FRAX', 'LINK', 'GMX', 'USDT',
                                                                  'USDC', 'UNI', 'DAI', 'esGMX')) -> Dict:
        # type: ignore

        balance_dict: Dict[str,float] = {}

        for token in token_iterable:
            if token != 'ETH':
                checker = self.conn.eth.contract(address=TokenAddressEnumType[token].value,
                                                 abi=TokenAbiEnumType[token].value)
                balance_dict[token] = checker.functions.balanceOf(self.wallet_adr).call()/\
                                      10 ** TokenDecimalsEnumType[token].value
            else:
                balance_dict[token] = self.conn.eth.get_balance(self.wallet_adr)/10**TokenDecimalsEnumType[token].value

        return balance_dict


if __name__ == '__main__':
    start_time = time.time()
    test = MetamaskInfoFetcher()
    print(test.get_balance_amount())
    print(f'process time is: {time.time() - start_time}')
