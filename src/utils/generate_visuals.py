"""
Visualization Suite for QuadNova.
Generates 5 professional charts for the technical report.
"""

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import numpy as np

def generate_charts():
    print("=== QUADNOVA VISUALIZATION SUITE ===")
    
    chart_path = Path("outputs/charts")
    chart_path.mkdir(parents=True, exist_ok=True)
    
    # Set professional style
    sns.set_theme(style="whitegrid")
    plt.rcParams['figure.figsize'] = (10, 6)

    # 1. Feature Importance Chart
    imp_path = Path("models/feature_importance.csv")
    if imp_path.exists():
        df_imp = pd.read_csv(imp_path).head(10)
        plt.figure()
        sns.barplot(data=df_imp, x='Importance_Abs', y='Feature', palette='viridis')
        plt.title("Top 10 Drivers of Latent Potential", fontsize=15)
        plt.xlabel("Absolute Coefficient Weight")
        plt.tight_layout()
        plt.savefig(chart_path / "feature_importance.png")
        print("SAVED: feature_importance.png")

    # 2. Rejection Reason Chart (Bar Chart is better for imbalanced data)
    rej_path = Path("outputs/evidence/rejected_reason_counts.csv")
    if rej_path.exists():
        df_rej = pd.read_csv(rej_path)
        # Aggregate by reason
        reason_sums = df_rej.groupby('rejection_reason')['count'].sum().sort_values(ascending=True)
        plt.figure()
        # Use log scale if the difference is massive (98% vs 1%)
        ax = reason_sums.plot(kind='barh', color=sns.color_palette('viridis', len(reason_sums)))
        plt.title("Data Forensics: Rejection Reasons (Trapped Anomalies)", fontsize=15)
        plt.xlabel("Number of Records")
        plt.ylabel("")
        
        # Add labels to the end of bars
        for i, v in enumerate(reason_sums):
            ax.text(v + 100, i, str(v), color='black', va='center', fontweight='bold')
            
        plt.tight_layout()
        plt.savefig(chart_path / "rejection_summary.png")
        print("SAVED: rejection_summary.png (Upgraded to Bar Chart)")

    # 3. Prediction Distribution
    pred_path = Path("outputs/predictions/quadnova_predictions.csv")
    if pred_path.exists():
        df_pred = pd.read_csv(pred_path)
        plt.figure()
        sns.histplot(df_pred['Maximum_Monthly_Liters'], bins=50, kde=True, color='teal')
        plt.title("Distribution of Predicted Latent Potential (Liters)", fontsize=15)
        plt.xlabel("Maximum Monthly Liters")
        plt.tight_layout()
        plt.savefig(chart_path / "prediction_distribution.png")
        print("SAVED: prediction_distribution.png")

    # 4. Outlet Segmentation Chart
    bi_path = Path("outputs/predictions/business_intelligence_report.csv")
    if bi_path.exists():
        df_bi = pd.read_csv(bi_path)
        plt.figure()
        segment_counts = df_bi['outlet_segment'].value_counts()
        sns.barplot(x=segment_counts.values, y=segment_counts.index, palette='magma')
        plt.title("Strategic Outlet Segmentation", fontsize=15)
        plt.xlabel("Number of Outlets")
        plt.tight_layout()
        plt.savefig(chart_path / "outlet_segments.png")
        print("SAVED: outlet_segments.png")

    # 5. Province Demand "Heatmap"
    # Using Distributor IDs to map to Provinces
    if bi_path.exists():
        # Load full features to get Distributor_ID
        feat_path = Path("data/gold/model_features.csv")
        if feat_path.exists():
            df_feat = pd.read_csv(feat_path, usecols=['Outlet_ID', 'Distributor_ID'])
            df_map = df_bi.merge(df_feat, on='Outlet_ID')
            
            def get_province(dist_id):
                if '_W_' in str(dist_id): return 'Western'
                if '_C_' in str(dist_id): return 'Central'
                if '_NW_' in str(dist_id): return 'North-Western'
                if '_S_' in str(dist_id): return 'Southern'
                return 'Other'
            
            df_map['Province'] = df_map['Distributor_ID'].apply(get_province)
            prov_demand = df_map.groupby('Province')['Maximum_Monthly_Liters'].sum().sort_values(ascending=False)
            
            plt.figure()
            sns.barplot(x=prov_demand.index, y=prov_demand.values, palette='rocket')
            plt.title("Estimated Total Demand Potential by Province", fontsize=15)
            plt.ylabel("Total Liters Potential")
            plt.tight_layout()
            plt.savefig(chart_path / "province_heatmap.png")
            print("SAVED: province_heatmap.png")

    print("---------------------------------")
    print(f"Visuals ready at: {chart_path}")
    print("=== VISUALS GENERATED ===")

if __name__ == "__main__":
    generate_charts()
