"""
Promotional budget allocation business constraints.

Defines all business rules and limit parameters for the LKR 5M Western 
Province trade spend optimization, including per-outlet bounds, distributor 
fairness floors, and exclusion thresholds.
"""

# ─────────────────────────────────────────────────────────────────
#  TOTAL BUDGET
# ─────────────────────────────────────────────────────────────────
TOTAL_WP_BUDGET_LKR = 5_000_000          # LKR 5 million for Western Province

# ─────────────────────────────────────────────────────────────────
#  PROVINCE FILTER
# ─────────────────────────────────────────────────────────────────
ELIGIBLE_PROVINCE   = "Western"           # Only Western Province outlets qualify

# ─────────────────────────────────────────────────────────────────
#  PER-OUTLET SPEND BOUNDS
# ─────────────────────────────────────────────────────────────────
MIN_SPEND_PER_OUTLET_LKR = 5_000         # Minimum trade spend per selected outlet
MAX_SPEND_PER_OUTLET_LKR = 100_000       # Maximum trade spend per selected outlet

# ─────────────────────────────────────────────────────────────────
#  OUTLET ELIGIBILITY THRESHOLDS
# ─────────────────────────────────────────────────────────────────
MIN_CONFIDENCE_SCORE     = 30.0          # Exclude outlets below this confidence
MIN_POTENTIAL_GAP_LITERS = 50.0          # Exclude outlets with near-zero upside

# ─────────────────────────────────────────────────────────────────
#  DISTRIBUTOR FAIRNESS FLOORS (Western Province)
#  Each of the 3 WP distributors must receive a guaranteed minimum allocation
# ─────────────────────────────────────────────────────────────────
WP_DISTRIBUTORS = ["DIST_W_01", "DIST_W_02", "DIST_W_03"]
DISTRIBUTOR_MIN_ALLOCATION_LKR = 500_000  # Floor per distributor (~10% of total each)

# ─────────────────────────────────────────────────────────────────
#  ALLOCATION STRATEGY WEIGHTS
# ─────────────────────────────────────────────────────────────────
# The optimizer scores each outlet as a weighted combination of:
#   - risk_adjusted_roi   : primary profit driver
#   - potential_gap       : raw volume opportunity
#   - spatial_opportunity_score : geographic footfall context
ROI_WEIGHT            = 0.60
POTENTIAL_GAP_WEIGHT  = 0.30
SPATIAL_WEIGHT        = 0.10
