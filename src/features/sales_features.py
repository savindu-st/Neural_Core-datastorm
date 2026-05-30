"""
Historical sales-based feature engineering.

Calculates aggregated behavioral, recency, and trend features from cleaned 
silver transaction history and outputs gold sales features.
"""

import pandas as pd
import numpy as np
import logging
from pathlib import Path
from src.utils.config import load_config

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def calculate_sales_features():
    logger.info("Starting Sales Feature Engineering...")
    config = load_config()
    
    silver_path = Path(config["data"]["silver_path"])
    gold_path = Path(config["data"]["gold_path"])
    gold_path.mkdir(parents=True, exist_ok=True)
    
    input_file = silver_path / "clean_transactions.csv"
    output_file = gold_path / "sales_features.csv"
    
    if not input_file.exists():
        logger.error(f"Silver cleaned transactions not found at: {input_file}")
        raise FileNotFoundError(f"Missing clean transactions: {input_file}")
        
    # Read transactions
    logger.info("Loading clean transactions...")
    df = pd.read_csv(input_file, dtype={"Outlet_ID": "str", "Distributor_ID": "str"})
    
    # 1. Group by Outlet and Period (Year-Month) to get monthly volumes
    monthly_tx = df.groupby(['Outlet_ID', 'Year', 'Month']).agg({
        'Volume_Liters': 'sum'
    }).reset_index()
    
    # Create unified monthly period representation (Year * 12 + Month)
    monthly_tx['Period'] = monthly_tx['Year'] * 12 + monthly_tx['Month']
    
    # Find all unique periods in the dataset chronologically
    all_periods = sorted(monthly_tx['Period'].unique())
    num_total_periods = len(all_periods)
    logger.info(f"Detected {num_total_periods} unique monthly periods in the transaction database.")
    
    # Pivot to have Outlets as rows, Periods as columns, filled with 0.0 for missing months
    logger.info("Pivoting transactions into monthly timeline...")
    pivot_df = monthly_tx.pivot(index='Outlet_ID', columns='Period', values='Volume_Liters').fillna(0.0)
    
    # 2. Basic Aggregations
    logger.info("Calculating basic monthly statistics...")
    avg_monthly = pivot_df.mean(axis=1)
    max_monthly = pivot_df.max(axis=1)
    min_monthly = pivot_df.min(axis=1)
    std_monthly = pivot_df.std(axis=1)
    
    # Coefficient of variation (volatility)
    sales_volatility = std_monthly / (avg_monthly + 1e-6)
    
    # 3. Recency and Trend Features (Recent 3 and 6 Months)
    logger.info("Calculating recency and trend metrics...")
    
    # Get last 3 and last 6 periods from the sorted unique list
    last_3_periods = all_periods[-3:] if num_total_periods >= 3 else all_periods
    last_6_periods = all_periods[-6:] if num_total_periods >= 6 else all_periods
    
    # Filter pivoted columns to calculate averages
    recent_3_avg = pivot_df[last_3_periods].mean(axis=1)
    recent_6_avg = pivot_df[last_6_periods].mean(axis=1)
    
    # Sales Trend: linear regression slope over the last 6 months
    # x is months [1, 2, ..., 6]
    # y is the monthly volumes for each outlet in last_6_periods
    y_trend = pivot_df[last_6_periods].values # shape: (num_outlets, 6)
    n_trend = y_trend.shape[1]
    x_trend = np.arange(1, n_trend + 1)
    
    # Vectorized slope calculation
    x_mean = np.mean(x_trend)
    y_mean = np.mean(y_trend, axis=1, keepdims=True)
    
    num = np.sum((x_trend - x_mean) * (y_trend - y_mean), axis=1)
    den = np.sum((x_trend - x_mean)**2)
    
    slopes = num / den
    
    # 4. Frequencies
    logger.info("Calculating order frequency metrics...")
    # Active purchase months: months where volume was > 0
    active_months_count = (pivot_df > 0.0).sum(axis=1)
    purchase_frequency = active_months_count / num_total_periods
    zero_sales_months = num_total_periods - active_months_count
    
    # Compile features DataFrame
    sales_features = pd.DataFrame({
        'Outlet_ID': pivot_df.index,
        'avg_monthly_liters': avg_monthly.values,
        'max_monthly_liters': max_monthly.values,
        'min_monthly_liters': min_monthly.values,
        'std_monthly_liters': std_monthly.values,
        'recent_3_month_avg': recent_3_avg.values,
        'recent_6_month_avg': recent_6_avg.values,
        'purchase_frequency': purchase_frequency.values,
        'sales_trend': slopes,
        'sales_volatility': sales_volatility.values,
        'zero_sales_months': zero_sales_months.values
    })
    
    # Save output to Gold
    sales_features.to_csv(output_file, index=False)
    logger.info(f"Sales features calculated successfully and saved to: {output_file} ({len(sales_features)} outlets)")

if __name__ == "__main__":
    calculate_sales_features()
