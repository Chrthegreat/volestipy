import pandas as pd
import matplotlib.pyplot as plt
import os

def plot_results(csv_file, start_row=0):
    """Reads the benchmark CSV and plots data starting from start_row."""
    if not os.path.exists(csv_file):
        print(f"Error: {csv_file} was not generated or found.")
        return

    df = pd.read_csv(csv_file, skipinitialspace=True)
    df.columns = df.columns.str.strip()

    if start_row > 0:
        df = df.iloc[start_row:]

    if df.empty:
        print("No new data to plot.")
        return

    print(f"Plotting {len(df)} new rows of data...")

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))

    for method_name, method_data in df.groupby('Method'):
        method_data = method_data.sort_values(by='Dimension')
        
        ax1.plot(method_data['Dimension'], method_data['Time_Sec'], 
                 marker='o', label=method_name.strip())
        
        ax2.plot(method_data['Dimension'], method_data['Mixing_Ratio'], 
                 marker='o', label=method_name.strip())

    ax1.set_yscale('log')
    ax1.set_title('Time vs. Dimension')
    ax1.set_xlabel('Dimension')
    ax1.set_ylabel('Total Algorithm Time (Seconds)')
    ax1.grid(True, which="both", linestyle='--', alpha=0.7)
    ax1.legend()

    ax2.set_yscale('log')
    ax2.set_title('Mixing Ratio vs. Dimension')
    ax2.set_xlabel('Dimension')
    ax2.set_ylabel('Mixing Ratio (Steps / ESS)')
    ax2.grid(True, which="both", linestyle='--', alpha=0.7)
    ax2.legend()

    plt.tight_layout()
    plt.show()

if __name__ == "__main__":
    # If run directly, plot everything (start_row=0)
    plot_results("benchmark_results.csv")