"""
src/stayline/modeling/thresholds.py
-------------------------------------
Calculates optimal thresholds based on expected net value.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.metrics import f1_score, precision_recall_curve

from stayline.config import get_assumptions, update_risk_thresholds


def find_optimal_threshold(y_true: np.ndarray, y_prob: np.ndarray, monthly_charges: np.ndarray) -> tuple[float, float, float]:
    """
    Find the threshold that maximizes Expected Net Value (ENV).
    Also finds the F1-optimal threshold and a recall-target threshold.
    """
    asm = get_assumptions().retention_offer
    
    thresholds = np.linspace(0.01, 0.99, 99)
    best_env = -np.inf
    best_t = 0.5
    
    for t in thresholds:
        predicted_positives = (y_prob >= t)
        
        # We only spend money on those we predict positive
        contacts = predicted_positives.sum()
        cost = contacts * asm.offer_cost_per_subscriber
        
        # We only save true positives
        true_positives = predicted_positives & (y_true == 1)
        expected_saves = true_positives.sum() * asm.assumed_save_rate
        
        # Revenue saved is based on their actual monthly charge
        if true_positives.sum() > 0:
            avg_charge = monthly_charges[true_positives].mean()
        else:
            avg_charge = 0
            
        gross_revenue = expected_saves * avg_charge * asm.value_horizon_months
        env = gross_revenue - cost
        
        if env > best_env:
            best_env = env
            best_t = t
            
    # F1 optimal
    precisions, recalls, f1_thresholds = precision_recall_curve(y_true, y_prob)
    f1_scores = 2 * (precisions * recalls) / (precisions + recalls + 1e-9)
    best_f1_idx = np.argmax(f1_scores)
    f1_opt_t = f1_thresholds[best_f1_idx] if best_f1_idx < len(f1_thresholds) else 0.5
    
    # Update global config with risk bands (High = ENV optimal, Medium = F1 optimal if lower)
    high_t = best_t
    med_t = min(best_t * 0.7, f1_opt_t)
    update_risk_thresholds(high_t, med_t)
    
    return float(best_t), float(f1_opt_t), float(best_env)
