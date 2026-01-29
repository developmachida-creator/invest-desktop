import tkinter as tk
import yfinance as yf
import matplotlib.pyplot as plt
import signal
import sys
from tkinter import messagebox
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from datetime import datetime

# --- 1. データ取得の責務 ---
def fetch_stock_data(ticker):
    """短期(5), 中期(25), 長期(75)の移動平均と出来高データを取得"""
    try:
        # 株価の取得。存在しないTickerが来た場合はNoneを返す。
        stock = yf.Ticker(ticker)
        df = stock.history(period="6mo") 
        if df.empty:
            return None
        
        # 移動平均線の計算
        df['5MA']  = df['Close'].rolling(window=5).mean()
        df['25MA'] = df['Close'].rolling(window=25).mean()
        df['75MA'] = df['Close'].rolling(window=75).mean()
        
        return df
    except Exception:
        return None

# --- 2. 描画の責務 ---
def draw_chart(df, ticker, ax1, ax2):
    """
    ax1: 上段（価格 + 移動平均線）
    ax2: 下段（出来高）
    """
    ax1.clear()
    ax2.clear()
    
    # 直近60日分を表示
    plot_df = df.tail(60)
    
    # --- 上段: 価格チャート ---
    ax1.plot(plot_df.index, plot_df['Close'], label="Price", color='#1f2937', linewidth=2, alpha=0.8)
    ax1.plot(plot_df.index, plot_df['5MA'],  label="5MA", color='#3b82f6', linewidth=1.2)
    ax1.plot(plot_df.index, plot_df['25MA'], label="25MA", color='#ef4444', linewidth=1.5) # サポート線
    ax1.plot(plot_df.index, plot_df['75MA'], label="75MA", color='#10b981', linewidth=1.2)
    
    ax1.set_title(f"{ticker} - Analysis", fontsize=12, fontweight='bold')
    ax1.legend(fontsize=8, loc='upper left', frameon=True)
    ax1.grid(True, linestyle='--', alpha=0.3)
    # 上段のX軸ラベルは非表示（下段と共有するため）
    plt.setp(ax1.get_xticklabels(), visible=False)

    # --- 下段: 出来高チャート ---
    # 前日より高い日は緑、低い日は赤で色分けすると見やすい
    colors = ['#10b981' if (plot_df['Close'].iloc[i] >= plot_df['Open'].iloc[i]) else '#ef4444' 
              for i in range(len(plot_df))]
    
    ax2.bar(plot_df.index, plot_df['Volume'], color=colors, alpha=0.7, width=0.7)
    ax2.set_ylabel("Volume", fontsize=9)
    ax2.grid(True, linestyle='--', alpha=0.3)
    
    # X軸の調整（日付を斜めにする）
    ax2.tick_params(axis='x', rotation=30, labelsize=8)
    
    fig.tight_layout()
    canvas.draw()

# --- 3. UI更新の司令塔 ---
def on_click_display():
    ticker = entry.get().strip().upper()
    if not ticker:
        messagebox.showwarning("Input Error", "Enter ticker (e.g., 7203.T)")
        return

    df = fetch_stock_data(ticker)
    
    if df is not None:
        latest_price = df['Close'].iloc[-1]
        time_str = datetime.now().strftime("%H:%M:%S")
        status_label.config(
            text=f"Ticker: {ticker}  |  Updated: {time_str}\nPrice: {latest_price:.1f} JPY",
            fg="#1f2937"
        )
        # 引数にax1, ax2を渡す
        draw_chart(df, ticker, ax1, ax2)
    else:
        status_label.config(text="Fetch Failed", fg="#ef4444")
        messagebox.showerror("Error", "Ticker not found or connection issue.")

# Ctrl + C を受け取った時の処理
def handle_sigint(sig, frame):
    print("\n[Ctrl + C を検知] 終了します...")
    safe_exit()

def safe_exit():
    # ウィンドウが存在するか確認してから処理
    try:
        if root.winfo_exists():
            root.quit()     # mainloopを止める
            root.destroy()  # ウィンドウを破棄
    except tk.TclError:
        pass # すでに破棄されている場合は無視
    
    # Pythonプロセス自体を終了させる（これで after の残骸も止まる）
    sys.exit(0)

# 「×」ボタンが押されたときに実行する関数
def on_closing():
    print("\n[×ボタンを検知] 終了します...")
    safe_exit()

# 一定時間（例: 500ミリ秒）ごとに、Python側に制御を戻して信号をチェックさせる
def check_signal():
    root.after(500, check_signal)



# --- 画面の構築 ---
root = tk.Tk()
root.title("Stock Trend & Volume Analyzer")
root.geometry("800x750")
root.configure(bg="#f3f4f6")

input_frame = tk.Frame(root, bg="#f3f4f6", pady=10)
input_frame.pack()

tk.Label(input_frame, text="証券コード:", bg="#f3f4f6").pack(side=tk.LEFT)
entry = tk.Entry(input_frame, font=("Consolas", 12))
entry.insert(0, "7203.T")
entry.pack(side=tk.LEFT, padx=10)

btn = tk.Button(input_frame, text="Enter", command=on_click_display,bg="#3b82f6", fg="white", font=("Arial", 10, "bold"), padx=20)
btn.pack(side=tk.LEFT)

status_label = tk.Label(root, text="証券コード入れてEnterを押してください。",font=("Arial", 11), bg="#f3f4f6", pady=10)
status_label.pack()

# グラフの土台（fig:外枠, ax1:上段の箱, ax2:下段の箱）を作成
# 2行1列で並べ、高さの比を3:1にする。X軸（日付）は上下で共有する設定。
# グラフの設計図を作成
fig, (ax1, ax2) = plt.subplots(
    2, 1,                 # 縦に2つ、横に1つのグラフを並べる
    figsize=(7, 6),       # 全体のサイズ（幅7インチ、高さ6インチ）
    sharex=True,          # 上下のグラフで横軸（日付）をピッタリ揃える
    gridspec_kw={         # グラフ間の比率を設定
        'height_ratios': [3, 1] # 上の箱を3、下の箱を1の高さにする
    }, 
    dpi=100               # 100dpiの解像度で作成
)

canvas = FigureCanvasTkAgg(fig, master=root)
canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

# メインループの前にこれを設定
signal.signal(signal.SIGINT, handle_sigint)
root.after(500, check_signal)

# ウィンドウが閉じられる時のプロトコルに、自作関数を紐付ける
root.protocol("WM_DELETE_WINDOW", on_closing)

root.mainloop()