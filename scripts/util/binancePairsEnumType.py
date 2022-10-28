from enum import Enum


class BinancePairsEnumType(Enum):
    BTCUSDT = 'BTCUSDT'
    BTCBUSD = 'BTCBUSD'
    ETHUSDT = 'ETHUSDT'
    ETHBUSD = 'ETHBUSD'
    LINKUSDT = 'LINKUSDT'
    LINKBUSD = 'LINKBUSD'
    UNIUSDT = 'UNIUSDT'
    UNIBUSD = 'UNIBUSD'


if __name__ == '__main__':
    for i in BinancePairsEnumType:
        print(i.value)

