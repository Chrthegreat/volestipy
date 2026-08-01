import volestipy
import os
import pandas as pd
from plot import plot_results

def main():
    csv_file = "benchmark_results.csv"
    
    existing_rows = 0
    if os.path.exists(csv_file):
        try:
            existing_rows = len(pd.read_csv(csv_file))
        except pd.errors.EmptyDataError:
            pass

    script_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.abspath(os.path.join(script_dir, "walk_config.json"))

    print("\n--- Starting C++ Benchmark ---")
    
    try:
        volestipy.run_benchmark([
            "--config", config_path
        ])
        print("--- C++ Benchmark Finished Successfully ---\n")
        
    except KeyboardInterrupt:
        print("\n\n!!! Benchmark Interrupted by User (Ctrl+C) !!!")
        print("Salvaging data collected so far...\n")
        
    except Exception as e:
        print(f"\n\n!!! Benchmark Crashed with Error: {e} !!!")
        print("Salvaging data collected so far...\n")
        
    finally:
        # Pass the row offset so we only plot the new stuff
        plot_results(csv_file, start_row=existing_rows)

if __name__ == "__main__":
    main()