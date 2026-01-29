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
        
        # 企業名の取得（日本株はshortName、外国株はlongNameが入りやすい）
        info = stock.info
        company_name = info.get('shortName') or info.get('longName') or ticker
        
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        
        # 移動平均線の計算
        df['5MA']  = df['Close'].rolling(window=5).mean()
        df['25MA'] = df['Close'].rolling(window=25).mean()
        df['75MA'] = df['Close'].rolling(window=75).mean()
        
        return df, company_name
    except Exception as e: # as e を追加してエラー内容を特定可能に
        print(f"Error fetching data: {e}")
        return None, None

# --- 2. 描画の責務 ---
def draw_chart(df, display_name, ax1, ax2):
    """
    display_name: グラフタイトルに表示する名前（企業名など）
    """
    ax1.clear()
    ax2.clear()
    
    plot_df = df.tail(60)
    
    # --- 上段: 価格チャート ---
    ax1.plot(plot_df.index, plot_df['Close'], label="Price", color='#1f2937', linewidth=2, alpha=0.8)
    ax1.plot(plot_df.index, plot_df['5MA'],  label="5MA", color='#3b82f6', linewidth=1.2)
    ax1.plot(plot_df.index, plot_df['25MA'], label="25MA", color='#ef4444', linewidth=1.5)
    ax1.plot(plot_df.index, plot_df['75MA'], label="75MA", color='#10b981', linewidth=1.2)
    
    # タイトルに企業名を表示
    ax1.set_title(f"{display_name} - Analysis", fontsize=12, fontweight='bold')
    ax1.legend(fontsize=8, loc='upper left', frameon=True)
    ax1.grid(True, linestyle='--', alpha=0.3)
    # 上段のX軸ラベルは非表示（下段と共有するため）
    plt.setp(ax1.get_xticklabels(), visible=False)

    # --- 下段: 出来高チャート ---
    # 前日より高い日は緑、低い日は赤で色分けすると見やすい
    colors = ['#10b981' if row['Close'] >= row['Open'] else '#ef4444' for _, row in plot_df.iterrows()]
    
    ax2.bar(plot_df.index, plot_df['Volume'], color=colors, alpha=0.7)
    ax2.set_ylabel("Volume", fontsize=9)
    ax2.grid(True, linestyle='--', alpha=0.3)

    # X軸の調整（日付を斜めにする）
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

    # 戻り値を2つ（データフレームと企業名）受け取る
    df, company_name = fetch_stock_data(ticker)
    
    if df is not None:
        latest_price = df['Close'].iloc[-1]
        time_str = datetime.now().strftime("%H:%M:%S")
        
        # ステータスラベルを更新
        status_label.config(
            text=f"[{ticker}] {company_name} | 株価: {latest_price:.1f} JPY ({time_str})",
            fg="#1f2937"
        )
        # 描画関数を呼ぶ（企業名を渡す）
        draw_chart(df, company_name, ax1, ax2)
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

def on_closing():
    safe_exit()

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

btn = tk.Button(input_frame, text="Enter", command=on_click_display, bg="#3b82f6", fg="white", font=("Arial", 10, "bold"), padx=20)
btn.pack(side=tk.LEFT)

status_label = tk.Label(root, text="証券コードを入れてEnterを押してください。", font=("Arial", 11), bg="#f3f4f6", pady=10)
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

signal.signal(signal.SIGINT, handle_sigint)
root.after(500, check_signal)
root.protocol("WM_DELETE_WINDOW", on_closing)

root.mainloop()