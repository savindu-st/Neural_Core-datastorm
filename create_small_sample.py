import pandas as pd
import numpy as np
from pathlib import Path

# Create SMALL sample data for testing
num_outlets = 100  # Small sample

outlet_ids = [f'OUT_{i:05d}' for i in range(num_outlets)]

# 1. Sample predictions
predictions = pd.DataFrame({
    'Outlet_ID': outlet_ids,
    'Maximum_Monthly_Liters': np.random.uniform(1500, 2500, num_outlets),
    'Current_Average_Sales': np.random.uniform(800, 1500, num_outlets),
    'Confidence_Score': np.random.uniform(0.7, 0.95, num_outlets)
})

# 2. Sample segments
segments = pd.DataFrame({
    'Outlet_ID': outlet_ids,
    'Segment': np.random.choice(['High Potential Urban', 'Growing Rural', 'Stable Mature', 'Challenge'], num_outlets)
})

# 3. Sample drivers
drivers = []
driver_names = ['Location Score', 'Competitor Proximity', 'Demographics', 'Road Access', 'Population Density']
for outlet_id in outlet_ids:
    for driver in driver_names:
        drivers.append({
            'Outlet_ID': outlet_id,
            'driver_name': driver,
            'positive_impact': np.random.uniform(0, 10),
            'negative_impact': np.random.uniform(-10, 0)
        })

driver_df = pd.DataFrame(drivers)

# Save files
Path('data/gold').mkdir(parents=True, exist_ok=True)
predictions.to_csv('data/gold/predictions_sample.csv', index=False)
segments.to_csv('data/gold/outlet_segments.csv', index=False)
driver_df.to_csv('data/gold/model_driver_table.csv', index=False)

# 4. Create outlet explanations
explanations = []
for _, pred in predictions.iterrows():
    outlet_id = pred['Outlet_ID']
    seg = segments[segments['Outlet_ID'] == outlet_id]['Segment'].values[0]
    
    outlet_drivers = driver_df[driver_df['Outlet_ID'] == outlet_id]
    pos_drivers = outlet_drivers.nlargest(2, 'positive_impact')['driver_name'].tolist()
    neg_drivers = outlet_drivers.nsmallest(2, 'negative_impact')['driver_name'].tolist()
    
    potential = pred['Maximum_Monthly_Liters']
    confidence = pred['Confidence_Score']
    
    explanations.append({
        'Outlet_ID': outlet_id,
        'Predicted_Potential': potential,
        'Segment': seg,
        'Confidence_Level': confidence,
        'Top_Positive_Drivers': ', '.join(pos_drivers),
        'Top_Negative_Drivers': ', '.join(neg_drivers),
        'Recommended_Action': 'Increase trade spend allocation by 25-30%',
        'Business_Explanation': f'This {seg} outlet has potential of {potential:.0f}L monthly. Key opportunities: {", ".join(pos_drivers)}. Key constraints: {", ".join(neg_drivers)}. Recommend targeted trade spend increase.'
    })

exp_df = pd.DataFrame(explanations)
Path('outputs/predictions').mkdir(parents=True, exist_ok=True)
exp_df.to_csv('outputs/predictions/outlet_explanations.csv', index=False)

print(f'✅ Created sample datasets with {num_outlets} outlets')
print('\nOutlet Explanations Sample:')
print(exp_df.head())
