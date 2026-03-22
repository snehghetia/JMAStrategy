# paper_trader.py
import csv
import os
from datetime import datetime

class PaperTrader:
    def __init__(self, capital=100000.0, lot_size=1000, symbol="USDINR"):
        self.balance = capital
        self.lot_size = lot_size
        self.symbol = symbol

        self.position_open = False
        self.side = None
        self.entry = None
        self.sl = None
        self.tp = None

        self.realized_pnl = 0.0

        # Trailing SL state
        self.breakeven_done = False
        self.entry_time = None

        # CSV setup
        self.csv_file = "paper_trades.csv"
        self._init_csv()

    def _init_csv(self):
        if not os.path.exists(self.csv_file):
            with open(self.csv_file, mode="w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow([
                    "Time", "Symbol", "Side", "Entry",
                    "SL", "TP", "Exit", "PnL", "Balance", "Reason"
                ])

    def _log_csv(self, row):
        with open(self.csv_file, mode="a", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(row)

    # ===================== ENTRY =====================
    def enter_trade(self, side, entry, sl, tp):
        if self.position_open:
            return

        self.position_open = True
        self.side = side
        self.entry = entry
        self.sl = sl
        self.tp = tp
        self.entry_time = datetime.now()
        self.breakeven_done = False

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        self._log_csv([
            now, self.symbol, side,
            round(entry, 4),
            round(sl, 4),
            round(tp, 4),
            "", "", "", "ENTRY"
        ])

        print("\n📥 PAPER TRADE ENTRY")
        print(f"Side       : {side}")
        print(f"Entry      : {round(entry,4)}")
        print(f"SL         : {round(sl,4)}")
        print(f"TP         : {round(tp,4)}")
        print("-" * 50)

    # ===================== TRAILING SL =====================
    def update_trailing_sl(self, ltp, jma_slow, current_time):
        if not self.position_open:
            return

        current_time = current_time.to_pydatetime().replace(tzinfo=None)

        if (current_time - self.entry_time).seconds < 900:
            return

        entry = self.entry
        tp = self.tp
        old_sl = self.sl

        # ================= SELL =================
        if self.side == "SELL":
            profit_move = entry - ltp
            target_move = entry - tp

            # Phase 1 → Move SL to breakeven
            if not self.breakeven_done:
                if profit_move >= 0.4 * target_move:
                    self.sl = entry
                    self.breakeven_done = True
                    print(f"🔒 SL moved to Breakeven: {round(old_sl,4)} → {round(self.sl,4)}")

            # Phase 2 → Trail using JMA Slow
            else:
                new_sl = min(self.sl, jma_slow)
                if new_sl < self.sl:
                    self.sl = new_sl
                    print(f"🔁 Trailing SL (JMA): {round(old_sl,4)} → {round(self.sl,4)}")

        # ================= BUY =================
        elif self.side == "BUY":
            profit_move = ltp - entry
            target_move = tp - entry

            if not self.breakeven_done:
                if profit_move >= 0.4 * target_move:
                    self.sl = entry
                    self.breakeven_done = True
                    print(f"🔒 SL moved to Breakeven: {round(old_sl,4)} → {round(self.sl,4)}")

            else:
                new_sl = max(self.sl, jma_slow)
                if new_sl > self.sl:
                    self.sl = new_sl
                    print(f"🔁 Trailing SL (JMA): {round(old_sl,4)} → {round(self.sl,4)}")

    # ===================== EXIT =====================
    def check_exit(self, price):
        if not self.position_open:
            return

        exit_price = None
        reason = None

        # ================= BUY =================
        if self.side == "BUY":
            if price <= self.sl:
                exit_price = self.sl
                reason = "SL HIT"
            elif price >= self.tp:
                exit_price = self.tp
                reason = "TP HIT"

            if exit_price:
                pnl = (exit_price - self.entry) * self.lot_size

        # ================= SELL =================
        else:
            if price >= self.sl:
                exit_price = self.sl
                reason = "SL HIT"
            elif price <= self.tp:
                exit_price = self.tp
                reason = "TP HIT"

            if exit_price:
                pnl = (self.entry - exit_price) * self.lot_size

        if exit_price:
            self.balance += pnl
            self.realized_pnl += pnl

            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            self._log_csv([
                now, self.symbol, self.side,
                "", "", "",
                round(exit_price, 4),
                round(pnl, 2),
                round(self.balance, 2),
                reason
            ])

            print("\n📤 PAPER TRADE EXIT")
            print(f"Reason     : {reason}")
            print(f"Exit       : {round(exit_price,4)}")
            print(f"PnL        : ₹{round(pnl,2)}")
            print(f"Balance    : ₹{round(self.balance,2)}")
            print("-" * 50)

            # Reset trade
            self.position_open = False
            self.side = None
            self.entry = None
            self.sl = None
            self.tp = None
            self.entry_time = None
            self.breakeven_done = False
