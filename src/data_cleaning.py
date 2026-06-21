import pandas as pd
from pathlib import Path
import os

def read_excel_files(raw_data_path):
    """Read all Excel files from the specified directory."""
    excel_files = list(Path(raw_data_path).glob('*.xlsx')) + list(Path(raw_data_path).glob('*.xls'))
    
    if not excel_files:
        print(f"No Excel files found in {raw_data_path}")
        return []
    
    dataframes = []
    for file in excel_files:
        try:
            df = pd.read_excel(file, skiprows=4)  # Skip the first row if it's a header
            file_parts = file.stem.split('-')
            holding_date = pd.to_datetime(file_parts[1].strip(), format='%d %B %Y', errors='coerce')
            df['Holding Date'] = holding_date
            print(f"Loaded: {file.name}")
            dataframes.append((holding_date, df))
        except Exception as e:
            print(f"Error reading {file.name}: {e}")
    if dataframes:
        dataframes.sort(key=lambda x: x[0])  # Sort by holding date
        dataframes = [df for _, df in dataframes]
    return dataframes

def filter_relevant_rows(df, criteria=None):
    """Filter columns > Remove rows with unnecessary data"""
    req_cols = ['Holding Date', 'ISIN', 'Name Of the Instrument', 'Industry+ /Rating', 'Quantity', 'Market/ Fair Value (Rs. in Lacs.)']
    
    # Select only the required columns
    try:
        df = df[req_cols].rename(columns={'Name Of the Instrument': 'Name', 'Industry+ /Rating': 'Industry', 'Market/ Fair Value (Rs. in Lacs.)': 'MV(Lacs)'})
    except KeyError as e:
        print(f"Error in excel: {df['Holding Date'].iloc[0]}")
        print(f"Error occurred while renaming columns: {e}")
        raise e

    # Create a mask that turns True at the target and stays True
    mask = (df['ISIN'] == 'Sub Total').cummax()

    # Invert mask to keep rows before the target value
    df_filtered = df[~mask | (df['ISIN'] == 'Sub Total')]
    
    df_filtered = df_filtered.dropna(subset=['Name', 'Industry', 'Quantity'])
    return df_filtered

def combine_excel_files(raw_data_path, output_path, criteria=None):
    """Main pipeline: read, filter, and combine Excel files."""
    # Read all Excel files
    dataframes = read_excel_files(raw_data_path)
    
    if not dataframes:
        print("No data to process.")
        return
    
    # Filter relevant rows from each dataframe
    filtered_dfs = [filter_relevant_rows(df, criteria) for df in dataframes]
    
    # Combine all dataframes
    combined_df = pd.concat(filtered_dfs, ignore_index=True)
    
    # Remove duplicate rows
    combined_df = combined_df.drop_duplicates()
    
    # Create output directory if it doesn't exist
    output_dir = Path(output_path).parent
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Save to Excel
    combined_df.to_excel(output_path, index=False)
    print(f"Combined data saved to: {output_path}")
    
    return combined_df

if __name__ == "__main__":
    # Define paths
    base_dir = Path(__file__).parent.parent
    raw_data_path = base_dir / "data" / "raw"
    output_path = base_dir / "data" / "processed" / "hdfc_flexi_fund_holding_data.xlsx"
    
    # Run the pipeline
    combined_df = combine_excel_files(raw_data_path, output_path)
