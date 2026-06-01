"""
Rule-based outlet explanation generation without GenAI API dependency.
Creates business-friendly explanations from model drivers and predictions.
"""

import pandas as pd
import logging
from pathlib import Path
import os

# Always resolve paths from project root
PROJECT_ROOT = Path(__file__).resolve().parents[2]
os.chdir(PROJECT_ROOT)

logger = logging.getLogger(__name__)


def load_data():
    """Load prediction and driver data."""
    driver_table = pd.read_csv('data/gold/model_driver_table.csv')
    outlet_segments = pd.read_csv('data/gold/outlet_segments.csv')
    predictions = pd.read_csv('outputs/predictions/quadnova_predictions.csv')
    return driver_table, outlet_segments, predictions


def identify_top_drivers(outlet_id, driver_table, top_n=3):
    """Identify top positive and negative drivers for an outlet."""
    outlet_drivers = driver_table[driver_table['Outlet_ID'] == outlet_id].copy()
    
    if outlet_drivers.empty:
        return [], []
    
    # Assume driver table has impact columns
    if 'positive_impact' in outlet_drivers.columns:
        top_positive = outlet_drivers.nlargest(top_n, 'positive_impact')['driver_name'].tolist()
    else:
        top_positive = []
    
    if 'negative_impact' in outlet_drivers.columns:
        top_negative = outlet_drivers.nsmallest(top_n, 'negative_impact')['driver_name'].tolist()
    else:
        top_negative = []
    
    return top_positive, top_negative


def assign_recommended_action(segment, confidence_level, potential_gap):
    """Assign business action based on outlet characteristics."""
    actions = {
        'High Potential Urban': 'Increase trade spend allocation 50%+. Focus on market development.',
        'Growing Rural': 'Build foundation with structured training and incentives.',
        'Stable Mature': 'Maintain consistent support with market share protection tactics.',
        'Challenge': 'Review channel viability. Consider targeted interventions or exit.'
    }
    
    if confidence_level < 0.6:
        return 'Collect more sales data before action. Monitor closely.'
    
    if potential_gap > 50:
        return 'High opportunity. Prioritize for aggressive marketing push.'
    elif potential_gap > 20:
        return 'Moderate opportunity. Increase trade spend by 25-30%.'
    elif potential_gap > 0:
        return 'Low opportunity. Maintain current investment level.'
    else:
        return 'Review positioning. Outlet may be at market saturation.'


def generate_business_explanation(outlet_id, segment, potential, current_sales, 
                                  confidence, positive_drivers, negative_drivers):
    """Generate simple business explanation text."""
    gap = potential - current_sales if current_sales else potential
    
    explanation = f"""
This outlet has a predicted monthly potential of {potential:.0f}L against current average sales of {current_sales:.0f}L, 
representing a {gap:.0f}L growth opportunity (confidence: {confidence:.0%}).

Key factors boosting this score: {', '.join(positive_drivers) if positive_drivers else 'favorable location and demographic trends'}. 
Key constraints: {', '.join(negative_drivers) if negative_drivers else 'competitive pressure and limited current penetration'}.

This {segment} segment outlet should be prioritized for increased trade spend to unlock dormant demand.
""".strip()
    
    return explanation


def generate_outlet_explanations():
    """Main function to generate outlet explanations."""
    logger.info("Loading data for outlet reasoning...")
    driver_table, outlet_segments, predictions = load_data()
    
    explanations = []
    
    for _, row in predictions.iterrows():
        outlet_id = row['Outlet_ID']
        
        # Get segment info
        segment_info = outlet_segments[outlet_segments['Outlet_ID'] == outlet_id]
        segment = segment_info['outlet_segment'].values[0] if not segment_info.empty else 'Unknown'
        
        # Identify drivers
        positive_drivers, negative_drivers = identify_top_drivers(outlet_id, driver_table)
        
        # Get prediction metrics
        predicted_potential = row['Maximum_Monthly_Liters']
        current_sales = row.get('Current_Average_Sales', 0)
        confidence = row.get('Confidence_Score', 0.5)
        allocation = row.get('Trade_Spend_Allocation_LKR', 0)
        
        # Assign action
        action = assign_recommended_action(segment, confidence, predicted_potential - current_sales)
        
        # Generate explanation
        explanation = generate_business_explanation(
            outlet_id, segment, predicted_potential, current_sales, 
            confidence, positive_drivers, negative_drivers
        )
        
        explanations.append({
            'Outlet_ID': outlet_id,
            'Predicted_Potential': predicted_potential,
            'Segment': segment,
            'Confidence_Level': confidence,
            'Top_Positive_Drivers': ', '.join(positive_drivers),
            'Top_Negative_Drivers': ', '.join(negative_drivers),
            'Recommended_Action': action,
            'Business_Explanation': explanation
        })
    
    output_df = pd.DataFrame(explanations)
    output_path = 'outputs/predictions/outlet_explanations.csv'
    Path('outputs/predictions').mkdir(parents=True, exist_ok=True)
    output_df.to_csv(output_path, index=False)
    
    logger.info(f"Generated explanations for {len(output_df)} outlets. Saved to {output_path}")
    return output_df


if __name__ == '__main__':
    generate_outlet_explanations()
