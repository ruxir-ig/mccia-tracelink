import pandas as pd
df = pd.read_csv('production_log.csv')
missing = df[df['batch_id'].isna()]
known = df[df['batch_id'].notna()]
rule1_count = 0
rule2_count = 0
for idx, m_row in missing.iterrows():
    m_date = pd.to_datetime(m_row['date'])
    # same lot, same machine
    c_df1 = known[(known['input_lot_ref'] == m_row['input_lot_ref']) & (known['machine_id'] == m_row['machine_id'])]
    if not c_df1.empty:
        c_dates = pd.to_datetime(c_df1['date'])
        if (abs((c_dates - m_date).dt.days) <= 3).any():
            rule1_count += 1
            continue
    # same lot
    c_df2 = known[known['input_lot_ref'] == m_row['input_lot_ref']]
    if not c_df2.empty:
        c_dates = pd.to_datetime(c_df2['date'])
        if (abs((c_dates - m_date).dt.days) <= 7).any():
            rule2_count += 1
            
print("Rule 1 matches:", rule1_count)
print("Rule 2 matches:", rule2_count)
