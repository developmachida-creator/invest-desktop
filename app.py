import tkinter as tk
import yfinance as yf
import matplotlib.pyplot as plt
import pandas as pd
import signal
import sys
from tkinter import messagebox
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from datetime import datetime

# --- 1. データ取得の責務 ---
def fetch_stock_data(ticker):
    """短期(5), 中期(25), 長期(75)の移動平均、出来高、企業名を取得"""
    try:
        stock = yf.Ticker(ticker)
        df = stock.history(period="1y") 
        if df.empty:
            return None, None
        
        info = stock.info
        company_name = info.get('shortName') or info.get('longName') or ticker
        
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        
        # 移動平均線の計算
        df['5MA']  = df['Close'].rolling(window=5).mean()
        df['25MA'] = df['Close'].rolling(window=25).mean()
        df['75MA'] = df['Close'].rolling(window=75).mean()

        # --- ボリンジャーバンドの計算 (25日基準) ---
        std = df['Close'].rolling(window=25).std()
        df['Upper'] = df['25MA'] + (std * 2)
        df['Lower'] = df['25MA'] - (std * 2)

        # --- RSIの計算 (14日間) ---
        diff = df['Close'].diff()
        gain = diff.clip(lower=0)
        loss = -diff.clip(upper=0)
        avg_gain = gain.rolling(window=14).mean()
        avg_loss = loss.rolling(window=14).mean()
        rs = avg_gain / avg_loss
        df['RSI'] = 100 - (100 / (1 + rs))
        
        return df, company_name
    except Exception as e:
        print(f"Error fetching data: {e}")
        return None, None

# --- 2. 描画の責務 ---
def draw_chart(df, display_name, ax1, ax_rsi, ax2):
    ax1.clear()
    ax_rsi.clear()
    ax2.clear()
    
    plot_df = df.tail(60)
    
    # --- 上段: 価格チャート ---
    # ボリンジャーバンドを先に描画（塗りつぶし）
    ax1.fill_between(plot_df.index, plot_df['Lower'], plot_df['Upper'], color='#3b82f6', alpha=0.1, label="Bollinger(2σ)")
    ax1.plot(plot_df.index, plot_df['Upper'], color='#3b82f6', linestyle=':', linewidth=0.8, alpha=0.4)
    ax1.plot(plot_df.index, plot_df['Lower'], color='#3b82f6', linestyle=':', linewidth=0.8, alpha=0.4)
    
    ax1.plot(plot_df.index, plot_df['Close'], label="Price", color='#1f2937', linewidth=2, alpha=0.8)
    ax1.plot(plot_df.index, plot_df['5MA'],  label="5MA", color='#3b82f6', linewidth=1.2)
    ax1.plot(plot_df.index, plot_df['25MA'], label="25MA", color='#ef4444', linewidth=1.5)
    ax1.plot(plot_df.index, plot_df['75MA'], label="75MA", color='#10b981', linewidth=1.2)
    
    # タイトルに企業名を表示
    ax1.set_title(f"{display_name} - Analysis", fontsize=12, fontweight='bold')
    ax1.legend(fontsize=8, loc='upper left')
    ax1.grid(True, linestyle='--', alpha=0.3)

    # --- 中段: RSIチャート ---
    ax_rsi.plot(plot_df.index, plot_df['RSI'], color='#8b5cf6', linewidth=1.5, label="RSI(14)")
    # 70%(買われすぎ)と30%(売られすぎ)にラインを引く
    ax_rsi.axhline(70, color='#ef4444', linestyle='--', linewidth=1, alpha=0.5)
    ax_rsi.axhline(30, color='#3b82f6', linestyle='--', linewidth=1, alpha=0.5)
    ax_rsi.set_ylim(0, 100)
    ax_rsi.set_ylabel("RSI", fontsize=9)
    ax_rsi.grid(True, linestyle='--', alpha=0.3)
    ax_rsi.legend(fontsize=7, loc='upper left')

    # --- 下段: 出来高チャート ---
    colors = ['#10b981' if row['Close'] >= row['Open'] else '#ef4444' for _, row in plot_df.iterrows()]
    ax2.bar(plot_df.index, plot_df['Volume'], color=colors, alpha=0.7)
    ax2.set_ylabel("Volume", fontsize=9)
    ax2.grid(True, linestyle='--', alpha=0.3)

    # X軸の調整
    ax2.tick_params(axis='x', rotation=30, labelsize=8)
    ax2.xaxis.set_major_locator(plt.MaxNLocator(10))
    
    fig.tight_layout()
    canvas.draw()

# --- 3. UI更新の司令塔 ---
def on_click_display():
    ticker = entry.get().strip().upper()
    if not ticker:
        messagebox.showwarning("入力エラー", "Enter ticker (e.g., 7203.T)")
        return

    df, company_name = fetch_stock_data(ticker)
    
    if df is not None:
        latest_price = df['Close'].iloc[-1]
        time_str = datetime.now().strftime("%H:%M:%S")
        
        status_label.config(
            text=f"[{ticker}] {company_name} | 株価: {latest_price:.1f} JPY ({time_str})| RSI: {df['RSI'].iloc[-1]:.1f}",
            fg="#1f2937"
        )
        # 修正: ax_rsiを追加
        draw_chart(df, company_name, ax1, ax_rsi, ax2)
    else:
        status_label.config(text="Fetch Failed", fg="#ef4444")
        messagebox.showerror("Error", "Ticker not found or connection issue.")

# 終了処理関連
def handle_sigint(sig, frame):
    print("\n[Ctrl + C を検知] 終了します...")
    safe_exit()

def safe_exit():
    try:
        if root.winfo_exists():
            root.quit()
            root.destroy()
    except tk.TclError:
        pass
    sys.exit(0)
def on_closing(): safe_exit()
def check_signal(): root.after(500, check_signal)

# --- 画面の構築 ---
root = tk.Tk()
root.title("Stock Trend, RSI & Volume Analyzer")
root.geometry("800x850") # 高さを少し広げる
root.configure(bg="#f3f4f6")

input_frame = tk.Frame(root, bg="#f3f4f6", pady=10)
input_frame.pack()

tk.Label(input_frame, text="証券コード:", bg="#f3f4f6").pack(side=tk.LEFT)
entry = tk.Entry(input_frame, font=("Consolas", 12))
entry.insert(0, "7203.T")
entry.pack(side=tk.LEFT, padx=10)

btn = tk.Button(input_frame, text="Enter", command=on_click_display, bg="#3b82f6", fg="white", font=("Arial", 10, "bold"), padx=20)
btn.pack(side=tk.LEFT)

status_label = tk.Label(root, text="証券コードを入れてEnterを押してください。", font=("Arial", 11), bg="#f3f4f6", pady=10)
status_label.pack()

# グラフ設計図の修正 (3段構成)
fig, (ax1, ax_rsi, ax2) = plt.subplots(
    3, 1, 
    figsize=(7, 7), 
    sharex=True, 
    gridspec_kw={
        'height_ratios': [3, 1, 1] # RSIと出来高を同じ高さにする
    }, 
    dpi=100
)

canvas = FigureCanvasTkAgg(fig, master=root)
canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

signal.signal(signal.SIGINT, handle_sigint)
root.after(500, check_signal)
root.protocol("WM_DELETE_WINDOW", on_closing)

root.mainloop()