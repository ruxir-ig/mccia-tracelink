import pandas as pd
import numpy as np
import os
import random
import string

TARGET_ROWS = 50000
MALICIOUS_RATIO = 0.05

def generate_malicious_string():
    payloads = [
        "<script>alert('XSS')</script>",
        "'; DROP TABLE users; --",
        "../../etc/passwd",
        "admin' OR 1=1--",
        "NaN",
        "NULL",
        " ",
        "".join(random.choices(string.printable, k=250)), # long string
        "DROP TABLE raw_materials;",
        "{{7*7}}",
        "undefined",
        "[object Object]",
        "1/0"
    ]
    return random.choice(payloads)

def augment_csv(file_path):
    print(f"Augmenting {file_path}...")
    try:
        df = pd.read_csv(file_path)
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return

    if len(df) == 0:
        print(f"Empty dataframe for {file_path}")
        return

    # Calculate how many rows to add
    rows_to_add = TARGET_ROWS - len(df)
    if rows_to_add <= 0:
        print(f"{file_path} already has {len(df)} rows.")
        return

    # Sample existing rows to reach TARGET_ROWS
    augmented_df = df.sample(n=rows_to_add, replace=True).reset_index(drop=True)
    
    # Introduce some variations in numeric columns so they aren't exact duplicates
    numeric_cols = augmented_df.select_dtypes(include=[np.number]).columns
    for col in numeric_cols:
        std_dev = augmented_df[col].std()
        if pd.isna(std_dev) or std_dev == 0:
            std_dev = 1
        noise = np.random.normal(0, std_dev * 0.1, size=len(augmented_df))
        augmented_df[col] = augmented_df[col] + noise
        # If original was int, cast back
        if pd.api.types.is_integer_dtype(df[col]):
            augmented_df[col] = augmented_df[col].round().astype(int)

    # Combine with original
    final_df = pd.concat([df, augmented_df], ignore_index=True)

    # Inject malicious data
    num_malicious = int(TARGET_ROWS * MALICIOUS_RATIO)
    malicious_indices = random.sample(range(len(final_df)), num_malicious)

    cols = list(final_df.columns)
    for idx in malicious_indices:
        col_to_corrupt = random.choice(cols)
        col_type = final_df[col_to_corrupt].dtype
        
        if pd.api.types.is_numeric_dtype(col_type):
            corruption_type = random.choice(['negative', 'huge', 'nan', 'string'])
            if corruption_type == 'negative':
                final_df.at[idx, col_to_corrupt] = -abs(final_df.at[idx, col_to_corrupt]) * 10
            elif corruption_type == 'huge':
                final_df.at[idx, col_to_corrupt] = final_df.at[idx, col_to_corrupt] * 1000000
            elif corruption_type == 'nan':
                final_df.at[idx, col_to_corrupt] = np.nan
            elif corruption_type == 'string':
                # this might cast the whole column to object, which is good for malicious
                final_df.at[idx, col_to_corrupt] = generate_malicious_string()
        else:
            final_df.at[idx, col_to_corrupt] = generate_malicious_string()

    # Shuffle the dataframe to mix original, augmented, and malicious
    final_df = final_df.sample(frac=1).reset_index(drop=True)

    final_df.to_csv(file_path, index=False)
    print(f"Successfully augmented {file_path} to {len(final_df)} rows.")

if __name__ == "__main__":
    dummy_data_dir = r"c:\Users\Harsh Jain\Desktop\PROJECTS\MMCIA\mccia-tracelink\Dummy Data"
    if not os.path.exists(dummy_data_dir):
        print(f"Directory {dummy_data_dir} not found.")
    else:
        for filename in os.listdir(dummy_data_dir):
            if filename.endswith(".csv"):
                augment_csv(os.path.join(dummy_data_dir, filename))
