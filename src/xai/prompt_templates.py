"""
GenAI explanation prompt templates for outlet sales potential.
"""

OUTLET_EXPLANATION_PROMPT = """You are a business analyst explaining outlet sales potential to a beverage company executive.

Outlet ID: {Outlet_ID}
Predicted Potential: {Maximum_Monthly_Liters}
Current Average Sales: {avg_monthly_liters}
Potential Gap: {potential_gap}
Top Positive Drivers: {positive_drivers}
Top Negative Drivers: {negative_drivers}
Competitor Level: {competition_level}
Confidence Score: {confidence_score}
Recommended Spend: {Trade_Spend_Allocation_LKR}

Write a simple business explanation in 4 sentences:
1. Why the outlet received this score.
2. What factors increased the score.
3. What factors reduced or constrained the score.
4. What action the sales team should take."""

BUDGET_ALLOCATION_PROMPT = """Summarize budget allocation strategy for province: {province}

Total Budget: {total_budget}
Number of Outlets: {outlet_count}
Expected Incremental Revenue: {expected_revenue}
Risk-Adjusted ROI: {roi}

Generate a 3-sentence executive summary of the allocation strategy and expected outcomes."""

SEGMENT_ANALYSIS_PROMPT = """Analyze outlet segment: {segment}

Segment Characteristics: {characteristics}
Average Potential: {avg_potential}
Average Current Sales: {avg_current_sales}
Count: {outlet_count}
Recommendations: {recommendations}

Generate strategic recommendations for this segment in 2-3 sentences."""
