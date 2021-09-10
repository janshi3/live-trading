import json
import threading
import time
import websocket

from config import *


def on_open(conn_id):
    print("Connected!")


def on_error(conn_id, error):
    print(f"Error: {error}")


def draw_candle(c_open, c_close, c_high, c_low):
    print(f"Open: {c_open}, // Close: {c_close}, // High: {c_high}, // Low: {c_low}")


def get_prev_data(data, ticks):
    index = -1-ticks
    return data[index]


# Indicators
def sma(data, length, offset=0):
    ma_sum = 0
    for i in range(length):
        ma_sum += get_prev_data(data, i+offset)
    return ma_sum/length


def ema(data, length):
    multiplier = 2/(length+1)
    prev_multiplier = 1-multiplier
    close = get_prev_data(data, 0)
    return close * multiplier + sma(data, length, offset=1) * prev_multiplier


def wma(data, length):
    wma_sum = 0
    period_sum = 0
    for i in range(length):
        close = get_prev_data(data, i)
        period = length-i
        close *= period
        period_sum += period
        wma_sum += close
    return wma_sum / period_sum


class Trading:
    def __init__(self):
        # Variables
        self.balance = 1000
        self.run_up = 0
        self.draw_down = 0
        self.asset = 0
        self.entry_price = 0
        self.long = False
        self.recent_price = 0
        self.recent_high = 0
        self.recent_low = 0
        self.arr_closing_price = []
        self.arr_high = []
        self.arr_low = []

        # Locks
        self.recent_price_lock = threading.Lock()
        self.recent_high_lock = threading.Lock()
        self.recent_low_lock = threading.Lock()
        self.arr_closing_price_lock = threading.Lock()
        self.arr_high_lock = threading.Lock()
        self.arr_low_lock = threading.Lock()

        # Starting Threads
        receiver = threading.Thread(target=self.get_data, args=(), daemon=True)
        timer = threading.Thread(target=self.timer, args=(RESOLUTION,), daemon=True)
        receiver.start()
        timer.start()

    # Get Recent Price
    def on_message(self, ws, message):
        data = json.loads(message)
        price = float(data['p'])
        self.recent_price_lock.acquire()
        self.recent_price = price
        self.recent_price_lock.release()
        self.get_high_low(price)

    # Receive price stream
    def get_data(self,):
        ws = websocket.WebSocketApp(SOCKET, on_open=on_open, on_message=self.on_message, on_error=on_error)
        ws.run_forever()

    # Get recent high and low
    def get_high_low(self, price):
        self.recent_high_lock.acquire()
        if price > self.recent_high:
            self.recent_high = price
        self.recent_high_lock.release()

        self.recent_low_lock.acquire()
        if price < self.recent_low:
            self.recent_low = price
        self.recent_low_lock.release()

    # Get the current closing price
    def get_candle_close(self, res):
        self.recent_price_lock.acquire()
        self.arr_closing_price_lock.acquire()

        price = self.recent_price
        self.arr_closing_price.append(price)

        self.recent_price_lock.release()
        self.arr_closing_price_lock.release()

        self.get_candle_high_low(price)
        self.delete_data(res)

    def get_candle_high_low(self, price):
        self.recent_high_lock.acquire()
        self.arr_high_lock.acquire()

        self.arr_high.append(self.recent_high)
        self.recent_high = price

        self.recent_high_lock.release()
        self.arr_high_lock.release()

        self.recent_low_lock.acquire()
        self.arr_low_lock.acquire()

        self.arr_low.append(self.recent_low)
        self.recent_low = price

        self.recent_low_lock.release()
        self.arr_low_lock.release()

    # Delete the oldest closing price
    def delete_data(self, res):
        self.arr_closing_price_lock.acquire()
        if len(self.arr_closing_price) > MEM_LENGTH:
            self.arr_closing_price.pop(0)
        self.arr_closing_price_lock.release()

        self.arr_high_lock.acquire()
        if len(self.arr_high) > MEM_LENGTH:
            self.arr_high.pop(0)
        self.arr_high_lock.release()

        self.arr_low_lock.acquire()
        if len(self.arr_low) > MEM_LENGTH:
            self.arr_low.pop(0)
        self.arr_low_lock.release()

        self.enter_trade(res)

    # Candle calculation, strategy
    def enter_trade(self, res):
        self.arr_closing_price_lock.acquire()
        closing_list = self.arr_closing_price.copy()
        self.arr_closing_price_lock.release()

        self.arr_high_lock.acquire()
        high_list = self.arr_high.copy()
        self.arr_high_lock.release()

        self.arr_low_lock.acquire()
        low_list = self.arr_low.copy()
        self.arr_low_lock.release()

        if len(closing_list) > 2:
            c_close = get_prev_data(closing_list, 0)
            c_open = get_prev_data(closing_list, 1)
            c_high = get_prev_data(high_list, 0)
            c_low = get_prev_data(low_list, 0)
            draw_candle(c_open, c_close, c_high, c_low)
        if len(closing_list) > 11:
            print(ema(closing_list, 11))

        # Insert strategy logic here

    def timer(self, res):
        while True:
            time.sleep(res - time.time() % res)
            a = threading.Thread(target=self.get_candle_close, args=(res,), daemon=True)
            a.start()

    def __del__(self):
        print("Balance: $" + str(self.balance))
        print("Draw Down: $" + str(self.draw_down))
        print("Run Up: $" + str(self.run_up))


test = Trading()
if input() == "e":
    test.__del__()
