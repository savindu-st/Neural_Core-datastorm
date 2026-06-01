"""
Mathematical framework for estimating latent demand using Censored Regression (Tobit Model).

This module handles the 'uncapping' of demand by treating historical sales as 
right-censored observations where Demand >= Observed Sales.
"""

import numpy as np
import pandas as pd
from scipy.optimize import minimize
from scipy.stats import norm
import logging

logger = logging.getLogger(__name__)

class TobitModel:
    """
    A Tobit Regression model (Type I) for right-censored data.
    
    The model assumes: y* = Xb + e, where e ~ N(0, sigma^2)
    We observe y = min(y*, C) where C is the censoring limit.
    
    In our case, y is the observed Volume_Liters, and C is the 
    bottleneck (Supply/Credit limit).
    """
    
    def __init__(self):
        self.beta = None
        self.sigma = None
        self.features = None

    def _log_likelihood(self, params, X, y, censored_mask):
        """
        Log-likelihood for right-censored data.
        
        LL = sum(log(pdf((y - Xb)/s) / s)) for uncensored
           + sum(log(1 - cdf((y - Xb)/s))) for right-censored
        """
        beta = params[:-1]
        sigma = params[-1]
        
        if sigma <= 0:
            return 1e10
        
        mu = np.dot(X, beta)
        z = (y - mu) / sigma
        
        # Uncensored part (Normal PDF)
        ll_uncensored = norm.logpdf(z) - np.log(sigma)
        
        # Right-censored part (1 - CDF, which is the Survival Function)
        # Note: lifelines/scipy uses logsf for log(1-CDF)
        ll_censored = norm.logsf(z)
        
        # Combine
        total_ll = np.sum(ll_uncensored[~censored_mask]) + np.sum(ll_censored[censored_mask])
        
        return -total_ll # Return negative LL for minimization

    def fit(self, X, y, censored_mask):
        """
        Fits the Tobit model using Maximum Likelihood Estimation.
        
        Args:
            X: Feature matrix (n_samples, n_features)
            y: Target vector (observed sales)
            censored_mask: Boolean array where True indicates the data is censored (at the ceiling)
        """
        # Add intercept
        X_const = np.column_stack([np.ones(X.shape[0]), X])
        
        # Initial guess (OLS estimates)
        initial_beta = np.linalg.lstsq(X_const, y, rcond=None)[0]
        initial_sigma = np.std(y - np.dot(X_const, initial_beta))
        initial_params = np.append(initial_beta, initial_sigma)
        
        # Optimize
        res = minimize(
            self._log_likelihood, 
            initial_params, 
            args=(X_const, y, censored_mask),
            method='L-BFGS-B',
            bounds=[(None, None)] * len(initial_beta) + [(1e-6, None)]
        )
        
        if not res.success:
            logger.warning(f"MLE Optimization failed: {res.message}. Using OLS fallback.")
            self.beta = initial_beta
            self.sigma = initial_sigma
        else:
            self.beta = res.x[:-1]
            self.sigma = res.x[-1]
            
        return self

    def predict(self, X, method='mean', quantile=0.90):
        """
        Predicts the latent potential (uncensored value).

        Args:
            X: Feature matrix.
            method: 'mean' for the expected value of the latent distribution (Xb),
                    'quantile' for a high-potential estimate at the given quantile level.
            quantile: Quantile level to use when method='quantile' (default 0.90).
                      Configurable via config/params.yaml -> model.prediction_quantile.
        """
        X_const = np.column_stack([np.ones(X.shape[0]), X])
        latent_mean = np.dot(X_const, self.beta)

        if method == 'mean':
            return latent_mean
        elif method == 'quantile':
            # Potential as the Nth percentile of the demand distribution
            return latent_mean + norm.ppf(quantile) * self.sigma
        else:
            return latent_mean

