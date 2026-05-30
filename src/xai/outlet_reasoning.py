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

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def load_data():
    """Load prediction and driver data."""
    # Main predictions
    predictions = pd.read_csv('outputs/predictions/quadnova_predictions.csv')

    # Budget allocations — only has Outlet_ID + Trade_Spend_Allocation_LKR
    allocations = pd.read_csv('outputs/predictions/quadnova_budget_allocations.csv')

    # Segments — column is 'outlet_segment', not 'Segment'
    outlet_segments = pd.read_csv('data/gold/outlet_segments.csv')

    # Driver table — has top_positive_driver, top_negative_driver columns
    driver_table = pd.read_csv('data/gold/model_driver_table.csv')

    # Merge predictions with allocations and segments
    df = predictions.merge(allocations, on='Outlet_ID', how='left')
    df = df.merge(
        outlet_segments[['Outlet_ID', 'outlet_segment', 'confidence_score', 'potential_gap', 'business_recommendation']],
        on='Outlet_ID', how='left'
    )
    df = df.merge(
        driver_table[['Outlet_ID', 'top_positive_driver', 'top_negative_driver']],
        on='Outlet_ID', how='left'
    )

    return df


def assign_recommended_action(segment, confidence_level, potential_gap, business_rec):
    """Assign business action based on outlet characteristics."""
    # Use the pre-computed business_recommendation if available
    if pd.notna(business_rec) and business_rec:
        return business_rec

    if pd.isna(confidence_level) or confidence_level < 0.6:
        return 'Collect more sales data before action. Monitor closely.'

    if pd.isna(potential_gap):
        potential_gap = 0

    if potential_gap > 500:
        return 'High opportunity. Prioritize for aggressive marketing push and cooler deployment.'
    elif potential_gap > 200:
        return 'Moderate opportunity. Increase trade spend by 25-30% and add in-store visibility.'
    elif potential_gap > 0:
        return 'Low opportunity. Maintain current investment level and monitor trends.'
    else:
        return 'Review positioning. Outlet may be at or near market saturation.'


def generate_business_explanation(outlet_id, segment, potential, positive_driver,
                                  negative_driver, confidence, potential_gap):
    """Generate simple business explanation text."""
    seg = segment if pd.notna(segment) else 'General'
    pos = positive_driver if pd.notna(positive_driver) else 'favorable location and sales history'
    neg = negative_driver if pd.notna(negative_driver) else 'competitive pressure'
    gap = potential_gap if pd.notna(potential_gap) else 0
    conf = confidence if pd.notna(confidence) else 0.5

    explanation = (
        f"This outlet (ID: {outlet_id}) is classified as '{seg}' with a predicted monthly "
        f"potential of {potential:.0f}L and an estimated untapped opportunity of {gap:.0f}L "
        f"(confidence: {conf:.0%}). "
        f"The primary positive driver boosting this score is '{pos}', indicating strong underlying demand signals. "
        f"The key constraint holding back full potential is '{neg}', which the sales team should address. "
        f"Targeted trade spend and in-store activations at this outlet are recommended to unlock the identified growth gap."
    )
    return explanation


def generate_outlet_explanations():
    """Main function to generate outlet explanations."""
    logger.info("Loading data for outlet reasoning...")
    df = load_data()

    logger.info(f"Processing {len(df)} outlets...")
    explanations = []

    for _, row in df.iterrows():
        outlet_id = row['Outlet_ID']
        segment = row.get('outlet_segment', 'Unknown')
        confidence = row.get('confidence_score', 0.5)
        potential_gap = row.get('potential_gap', 0)
        predicted_potential = row['Maximum_Monthly_Liters']
        positive_driver = row.get('top_positive_driver', '')
        negative_driver = row.get('top_negative_driver', '')
        business_rec = row.get('business_recommendation', '')

        # Assign action
        action = assign_recommended_action(segment, confidence, potential_gap, business_rec)

        # Generate explanation
        explanation = generate_business_explanation(
            outlet_id, segment, predicted_potential,
            positive_driver, negative_driver, confidence, potential_gap
        )

        explanations.append({
            'Outlet_ID': outlet_id,
            'Predicted_Potential': predicted_potential,
            'Segment': segment if pd.notna(segment) else 'Unknown',
            'Confidence_Level': confidence if pd.notna(confidence) else 0.5,
            'Top_Positive_Drivers': positive_driver if pd.notna(positive_driver) else '',
            'Top_Negative_Drivers': negative_driver if pd.notna(negative_driver) else '',
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
