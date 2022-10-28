from web3 import HTTPProvider, Web3
import json
import requests
from requests.exceptions import Timeout, TooManyRedirects, ConnectionError
import ccxt
from typing import Optional, List, Dict, Iterable, Tuple
from dotenv import load_dotenv
import os
from util.tokensInfoEnumType import TokenAddressEnumType, TokenDecimalsEnumType, TokenAbiEnumType
from util.contractInfoEnumType import ContractAddressEnumType, ContractAbiEnumType
from web3.types import Address,ChecksumAddress
import time
import asyncio
from priceFetcher import PriceFetcher

load_dotenv()


class GLPDataFetcher:

    def __init__(self,
                 infura_api_key: Optional[str] =os.getenv('INFURA_API_KEY'),
                 wallet_adr: Optional[str] =os.getenv('WALLET_ADDRESS'),
                 gmx_index_assets: Tuple[str, ...] =('WBTC','WETH','LINK','UNI','FRAX','USDT','USDC','DAI')
                 ):

        infura_api_url = 'https://arbitrum-mainnet.infura.io/v3/'
        infura_api_url = infura_api_url + infura_api_key

        self.gmx_index_assets = gmx_index_assets

        self.conn = Web3(HTTPProvider(infura_api_url))
        self.wallet_adr = wallet_adr
        self.tokens_info = self._get_tokens_info()
        self._staked_glp_amount = self.get_staked_glp_amount()
        self._glp_supply = self._get_glp_supply()
        self.glp_price_dict = self.get_glp_price()


    def _get_glp_supply(self) -> float:
        glp_contract = self.conn.eth.contract(address=TokenAddressEnumType.GLP.value,
                                              abi=TokenAbiEnumType.GLP.value)
        glp_total_supply = glp_contract.functions.totalSupply().call()
        return glp_total_supply  / 10 ** TokenDecimalsEnumType.GLP.value

    def get_claimable_info(self):
        reward_reader = self.conn.eth.contract(address=ContractAddressEnumType.RewardReader.value,
                                                abi=ContractAbiEnumType.RewardReader.value)
        address_list = [ContractAddressEnumType.StakedGmxTracker.value,
                        ContractAddressEnumType.FeeGmxTracker.value,
                        ContractAddressEnumType.FeeGlpTracker.value,
                        ContractAddressEnumType.StakedGlpTracker.value
                        ]
        response = reward_reader.functions.getStakingInfo(self.wallet_adr, address_list).call()
        response = [amount / 10**18 for amount in response]

        weth_claimable = response[5] + response[10]
        weth_cumalative = response[8] + response[13]
        esgmx_claimable = response[0] + response[15]
        esgmx_cumalative = response[3] + response[18]
        # print(response)
        return {'weth_claimable':weth_claimable, 'weth_cumulative':weth_cumalative, 'esgmx_claimable':esgmx_claimable,
                'esgmx_cumulative':esgmx_cumalative}

    def get_glp_price(self) -> Dict:
        glp_manager = self.conn.eth.contract(address=ContractAddressEnumType.GLPManager.value,
                                             abi=ContractAbiEnumType.GLPManager.value)
        glp_supply = self._glp_supply


        glp_aum_buy = glp_manager.functions.getAum(
            True).call() / 10**30
        glp_aum_sell = glp_manager.functions.getAum(
            False).call() / 10**30


        return {'buy': glp_aum_buy / glp_supply, 'sell': glp_aum_sell / glp_supply}

    def get_exposure_amount(self):

        # calculate the holding GLP to total GLP ratio
        glp_supply = self._glp_supply
        staked_glp = self._staked_glp_amount
        ratio = staked_glp/glp_supply

        #fetch the pool amount of total GLP and fetch the price from coingecko and GMX

        pool_amount_dict = self._get_pool_amounts()
        exposure_dict = {}
        for symbol, amount in  pool_amount_dict.items():
            exposure = amount * ratio
            exposure_dict[symbol] = exposure

        return exposure_dict

    def get_exposure_total(self):
        pool_amount_dict = self._get_pool_amounts()
        exposure_dict = {}
        total_value = 0
        price_dict = PriceFetcher.get_assets_price_gmx()

        for symbol, amount in pool_amount_dict.items():
            total_value +=  amount * price_dict[symbol]

        for symbol, amount in  pool_amount_dict.items():
            exposure = amount * price_dict[symbol] / total_value
            exposure_dict[symbol] = exposure

        return exposure_dict

    def get_balance(self) -> float:
        staked_glp = self._staked_glp_amount
        glp_price_dict = self.glp_price_dict
        glp_mid_price = (glp_price_dict['buy'] + glp_price_dict['buy']) / 2

        return staked_glp * glp_mid_price

    def _get_pool_amounts(self):

        tokens_info: Dict[str, Dict] = self.tokens_info
        pool_amount_dict : Dict[str,float] = {}

        for symbol in tokens_info.keys():
             pool_amount_dict[symbol] = tokens_info[symbol]['pool_amount']
        return pool_amount_dict

    def _get_tokens_info(self) -> Dict:

        vault_adr: ChecksumAddress = ContractAddressEnumType.vault.value
        weth_adr: ChecksumAddress = TokenAddressEnumType.WETH.value
        usdg_amount: int = 0 # only used to call vault.getRedemptionAmount(token, _usdgAmount), in unit 10**30

        # GMX index address address
        token_adr: List[str] = [TokenAddressEnumType[token].value for token in self.gmx_index_assets]

        reader_contract = self.conn.eth.contract(address=ContractAddressEnumType.Reader.value,
                                                abi=ContractAbiEnumType.Reader.value)


        response = reader_contract.functions.getVaultTokenInfoV2(vault_adr, weth_adr, usdg_amount, token_adr).call()

        info_dict: Dict[str, Dict] = {}
        props_length: int = 14

        for round, symbol in enumerate(self.gmx_index_assets):
            for counter in range(props_length):
                if counter % 14 == 0:
                    pool_amount = response[round*14]/10**TokenDecimalsEnumType[symbol].value
                elif counter % 14 == 1:
                    reserved_amount = response[round*14 + 1]/10**TokenDecimalsEnumType[symbol].value
                elif counter % 14 == 12:
                    price_not_maximised = response[round * 14 + 12]/10**30

            info_dict[symbol] = {'pool_amount':pool_amount,
                                 'reserved_amount':reserved_amount,
                                 'price_not_maximised':price_not_maximised,
                                 }

        return info_dict

    def get_staked_gmx_amount(self) -> float:
        staked_gmx_tracker = self.conn.eth.contract(address=ContractAddressEnumType.StakedGmxTracker.value,
                                                  abi=ContractAbiEnumType.StakedGmxTracker.value)

        staked_gmx = staked_gmx_tracker.functions.depositBalances(self.wallet_adr,
                                                                  TokenAddressEnumType.GMX.value).call()

        return staked_gmx/10**TokenDecimalsEnumType.GMX.value

    def get_staked_esgmx_amount(self) -> float:
        staked_gmx_tracker = self.conn.eth.contract(address=ContractAddressEnumType.StakedGmxTracker.value,
                                                  abi=ContractAbiEnumType.StakedGmxTracker.value)

        staked_esgmx = staked_gmx_tracker.functions.depositBalances(self.wallet_adr,
                                                                  TokenAddressEnumType.esGMX.value).call()


        return staked_esgmx/10**TokenDecimalsEnumType.esGMX.value

    def get_staked_glp_amount(self) -> float:
        fee_glp_tracker = self.conn.eth.contract(address=ContractAddressEnumType.FeeGlpTracker.value,
                                                     abi=ContractAbiEnumType.FeeGlpTracker.value)

        staked_glp = fee_glp_tracker.functions.stakedAmounts(self.wallet_adr).call()

        return staked_glp/10 ** TokenDecimalsEnumType.GLP.value

    def get_assets_amounts_summary(self):
        exposure_amount = self.get_exposure_amount()


        return {'GMX':self.get_staked_gmx_amount(),
                'esGMX':self.get_staked_esgmx_amount(),
                'GLP':self._staked_glp_amount,
                'WBTC':exposure_amount['WBTC'],
                'WETH':exposure_amount['WETH'],
                'LINK':exposure_amount['LINK'],
                'UNI': exposure_amount['UNI'],
                'FRAX':exposure_amount['FRAX'],
                'USDT':exposure_amount['USDT'],
                'USDC':exposure_amount['USDC'],
                'DAI':exposure_amount['DAI']}

if __name__ == '__main__':
    start_time = time.time()
    test = GLPDataFetcher()


    print(test. get_assets_amounts_summary())
    print(f'process time is: {time.time() - start_time}')





