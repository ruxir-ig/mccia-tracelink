import sqlite3
import pandas as pd
from app.db import DB_PATH

conn = sqlite3.connect(DB_PATH)
df = pd.read_csv('../defect_complaints.csv')
print(df.columns.tolist())
print(df.head(3).to_dict('records'))
