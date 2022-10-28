from apscheduler.schedulers.blocking import BlockingScheduler  # type: ignore
import MySQLdb as mdb  # type: ignore
from dataProcessor import BalanceProcessor
from binanceAccountFetcher import BinanceAccountInfo
from typing import Dict, List
import datetime
from util.binancePairsEnumType import BinancePairsEnumType
import time


class DatabaseInserter:
    def __init__(self, db_host: str = 'localhost',
                 db_user: str = 'sec_user',
                 db_pass: str = 'password',
                 db_name: str = 'glp_database'
                 ):
        self.db_host = db_host
        self.db_user = db_user
        self.db_pass = db_pass
        self.db_name = db_name
        self.con = mdb.connect(host=self.db_host, user=self.db_user, password=self.db_pass, db=self.db_name)

        self.processor = BalanceProcessor()
        self.created_time = datetime.datetime.now()
        self.updated_time = datetime.datetime.now()

    def insert_summary_total_balance(self):
        table = 'summary_total_balance'
        # Create the insert string
        columns_str = (
            'created_date, updated_date, exchange_name, '
            'notional, wallet_balance, margin_ratio '
        )

        insert_string = ('%s, ' * 6)[:-2]
        final_string = f'INSERT INTO {table} ({columns_str}) VALUES ({insert_string})'
        data = self._obtain_summary_total_balance_data()
        cur = self.con.cursor()
        cur.executemany(final_string, data)
        self.con.commit()

    def _obtain_summary_total_balance_data(self):
        notional_dict = self.processor.get_total_notional_value_balance()

        data_list: List = []
        for exchange in notional_dict:
            created_time = self.created_time
            updated_time = self.updated_time
            exchange_name = exchange
            notional = notional_dict[exchange]

            if exchange == 'Binance':
                wallet_balance = sum(self.processor.get_binance_wallet_balances()['notional'].values())
                margin_ratio = BinanceAccountInfo().get_total_margin_ratio()
            else:
                wallet_balance = 0
                margin_ratio = 0
            data_list.append([created_time, updated_time, exchange_name, notional, wallet_balance, margin_ratio])

        return data_list

    def insert_binance_hedge_account(self):
        table = 'binance_hedge_account'
        columns_str = (
            'created_date, updated_date, position_amount, '
            'notional, funding_rate, quote, base, unrealized_profit '
        )

        insert_string = ('%s, ' * 8)[:-2]
        final_string = f'INSERT INTO {table} ({columns_str}) VALUES ({insert_string})'
        data = self._obtain_binance_hedge_account_data()
        cur = self.con.cursor()
        cur.executemany(final_string, data)
        self.con.commit()

    def _obtain_binance_hedge_account_data(self):
        hedge_dict = self.processor.binance_summary['hedge']

        data_list: List = []

        pairs = BinancePairsEnumType._member_names_

        for pair in pairs:
            created_time = self.created_time
            updated_time = self.updated_time

            data_list.append([created_time, updated_time, hedge_dict['positionAmt'][pair],
                              hedge_dict['notional'][pair], hedge_dict['funding_rate'][pair], hedge_dict['quote'][pair],
                              hedge_dict['base'][pair], hedge_dict['unrealizedProfit'][pair]])
        return data_list

    def insert_gmx_account(self):
        table = 'gmx_account'
        columns_str = (
            'created_date, updated_date, position_amount, '
            'notional, symbol, claimable, cumulative'
        )
        insert_string = ('%s, ' * 7)[:-2]
        final_string = f'INSERT INTO {table} ({columns_str}) VALUES ({insert_string})'
        data = self._obtain_gmx_account_data()
        cur = self.con.cursor()
        cur.executemany(final_string, data)
        self.con.commit()

    def _obtain_gmx_account_data(self):
        gmx_dict = self.processor.gmx_summary
        claimable_dict = self.processor.get_claimable_info()
        data_list: List = []

        tokens = gmx_dict['notional'].keys()

        for token in tokens:
            created_time = self.created_time
            updated_time = self.updated_time

            if token == 'WETH':
                data_list.append([created_time, updated_time, gmx_dict['amount'][token],
                                  gmx_dict['notional'][token], token, claimable_dict['weth_claimable'],
                                  claimable_dict['weth_cumulative']])
            elif token == 'esGMX':
                data_list.append([created_time, updated_time, gmx_dict['amount'][token],
                                  gmx_dict['notional'][token], token, claimable_dict['esgmx_claimable'],
                                  claimable_dict['esgmx_cumulative']])
            else:
                data_list.append([created_time, updated_time, gmx_dict['amount'][token],
                                  gmx_dict['notional'][token], token, 0,
                                  0])
        return data_list

    def insert_metamask_account(self) -> object:
        table = 'metamask_account'
        columns_str = (
            'created_date, updated_date, amount, '
            'notional, symbol'
        )
        insert_string = ('%s, ' * 5)[:-2]
        final_string = f'INSERT INTO {table} ({columns_str}) VALUES ({insert_string})'
        data = self._obtain_metamask_account_data()
        cur = self.con.cursor()
        cur.executemany(final_string, data)
        self.con.commit()

    def _obtain_metamask_account_data(self):
        metamask_dict = self.processor.metamask_summary
        data_list: List = []

        tokens = metamask_dict['notional'].keys()

        for token in tokens:
            created_time = self.created_time
            updated_time = self.updated_time

            data_list.append([created_time, updated_time, metamask_dict['amount'][token],
                              metamask_dict['notional'][token], token])
        return data_list

if __name__ == '__main__':
    start = time.time()
    test = DatabaseInserter()
    print(test.insert_metamask_account())
    print(test.insert_gmx_account())
    print(test.insert_binance_hedge_account())
    print(test.insert_summary_total_balance())
    print(time.time() - start)

