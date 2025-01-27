import alpaca_trade_api as alpaca
import requests
import asyncio

HEADERS = {'APCA-API-KEY-ID': 'PKC7ZL1YUV6X4FNQYBGB',
           'APCA-API-SECRET-KEY': '5fuIAYOaWqRKmptS0qmchBLmCnim8KxY8DNtaPHx'}

ALPACA_BASE_URL = 'https://paper-api.alpaca.markets'
DATA_URL = 'https://data.alpaca.markets'
rest_api = alpaca.REST('PKC7ZL1YUV6X4FNQYBGB', '5fuIAYOaWqRKmptS0qmchBLmCnim8KxY8DNtaPHx', ALPACA_BASE_URL)


waitTime = 3
min_arb_percent = 0.3

prices = {
    'ETH/USD': 0,
    'BTC/USD': 0,
    'ETH/BTC': 0
}

spreads = []


async def get_quote(symbol: str):
    '''
    Get quote data from Alpaca API
    '''

    try:
            quote = requests.get(
                '{0}/v1beta3/crypto/us/latest/orderbooks?symbols={1}'.format(DATA_URL, symbol), headers=HEADERS)
            prices[symbol] = quote.json()['orderbooks'][symbol]['a'][0]['p']
            if quote.status_code != 200:
                print("Undesirable response from Alpaca! {}".format(quote.json()))
            return False
    except Exception as e:
        print("There was an issue getting trade quote from Alpaca: {0}".format(e))
        return False

def post_alpaca_order(symbol, qty, side):
    '''
    Post an order to Alpaca
    '''
    try:
        order = requests.post(
            '{0}/v2/orders'.format(ALPACA_BASE_URL), headers=HEADERS, json={
                'symbol': symbol,
                'qty': qty,
                'side': side,
                'type': 'market',
                'time_in_force': 'gtc',
            })
        return order
    except Exception as e:
        print("There was an issue posting order to Alpaca: {0}".format(e))
        return False


async def check_arb():
    '''
    Check to see if an arbitrage condition exists
    '''
    ETH = prices['ETH/USD']
    BTC = prices['BTC/USD']
    ETHBTC = prices['ETH/BTC']
    DIV = ETH / BTC
    spread = abs(DIV - ETHBTC)
    BUY_ETH = 1000 / ETH
    BUY_BTC = 1000 / BTC
    BUY_ETHBTC = BUY_BTC / ETHBTC
    SELL_ETHBTC = BUY_ETH / ETHBTC

    # when BTC/USD is cheaper
    if DIV > ETHBTC * (1 + min_arb_percent/100):
        order1 = post_alpaca_order("BTCUSD", BUY_BTC, "buy")
        if order1.status_code == 200:
            order2 = post_alpaca_order("ETH/BTC", BUY_ETHBTC, "buy")
            if order2.status_code == 200:
                order3 = post_alpaca_order("ETHUSD", BUY_ETHBTC, "sell")
                if order3.status_code == 200:
                    print("Done (type 1) eth: {} btc: {} ethbtc {}".format(ETH, BTC, ETHBTC))
                    print("Spread: +{}".format(spread * 100))
                else:
                    post_alpaca_order("ETH/BTC", BUY_ETHBTC, "sell")
                    print("Bad Order 3")
                    exit()
            else:
                post_alpaca_order("BTCUSD", BUY_BTC, "sell")
                print("Bad Order 2")
                exit()
        else:
            print("Bad Order 1")
            exit()
 
    # when ETH/USD is cheaper
    elif DIV < ETHBTC * (1 - min_arb_percent/100):
        order1 = post_alpaca_order("ETHUSD", BUY_ETH, "buy")
        if order1.status_code == 200:
            order2 = post_alpaca_order("ETHBTC", BUY_ETH, "sell")
            if order2.status_code == 200:
                order3 = post_alpaca_order("BTCUSD", SELL_ETHBTC, "sell")
                if order3.status_code == 200:
                    print("Done (type 2) eth: {} btc: {} ethbtc {}".format(ETH, BTC, ETHBTC))
                    print("Spread: -{}".format(spread * 100))
                else:
                    post_alpaca_order("ETH/BTC", SELL_ETHBTC, "buy")  
                    print("Bad Order 3")                
                    exit()
            else:
                post_alpaca_order("ETHUSD", BUY_ETH, "sell")
                print("Bad Order 2")
                exit()    
        else:
            print("Bad order 1")
            exit()
    else:
        print("No arb opportunity, spread: {}".format(spread * 100))
        spreads.append(spread)

async def main():
        while True:
            task1 = loop.create_task(get_quote("ETH/USD"))
            task2 = loop.create_task(get_quote("BTC/USD"))
            task3 = loop.create_task(get_quote("ETH/BTC"))
            # Wait for the tasks to finish
            await asyncio.wait([task1, task2, task3])
            await check_arb()
            # # Wait for the value of waitTime between each quote request
            await asyncio.sleep(waitTime)


loop = asyncio.get_event_loop()
loop.run_until_complete(main())
loop.close()

