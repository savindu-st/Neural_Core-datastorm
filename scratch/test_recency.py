import pandas as pd
import numpy as np

# Create dummy tx data
tx = pd.DataFrame({
    'Outlet_ID': ['A', 'A', 'B'],
    'Year': [2023, 2023, 2023],
    'Month': [1, 2, 1],
    'Date': pd.to_datetime(['2023-01-01', '2023-02-01', '2023-01-01'])
})

max_date = pd.to_datetime(tx['Date']).max()
print(f"max_date: {max_date}")

recency = tx.groupby('Outlet_ID')['Date'].max().reset_index()
print(f"recency columns after groupby: {recency.columns}")

recency['inactive_days'] = (max_date - pd.to_datetime(recency['Date'])).dt.days
print(f"recency columns after assignment: {recency.columns}")

print(recency[['Outlet_ID', 'inactive_days']])
