import pandas as pd

import tensorflow as tf
from tensorflow import keras

from sklearn.metrics import mean_squared_error 
from sklearn.model_selection import train_test_split, KFold 
from sklearn.svm import SVR

from utils.estimator import ARIMAEstimator, GARCHEstimator

from statsmodels.tsa.arima.model import ARIMA

from skopt import BayesSearchCV
from skopt.space import Real, Integer

import xgboost as xgb 
from xgboost import XGBRegressor

from lightgbm import LGBMRegressor


class HyperparameterTuner:
    """
    Abstract class representing an object that tunes the hyperparameters of a 
    machine learning estimator.
    """
    def __init__(self):
        pass

    def bayesian_optimisation(self):
        """
        Abstract method implemented by subclasses
        """
        pass

    def grid_search(self):
        """
        Abstract method implemented by subclasses
        """
        pass

    def random_forest(self):
        """
        Abstract method implemented by subclasses
        """
        pass



class XGBTuner(HyperparameterTuner):
    """
    Concrete class representing an object that tunes an XGBRegressor object.
    """
    def __init__(self):
        super().__init__()
    
    def bayesian_optimisation(self, X, y):
        """
        WARNING: this takes a while to run!

        Tunes the hyperparameters for an XGBRegressor using Bayesian optimisation.
        Model performance is measured using k-fold cross validation with k=5.

        Returns:
            skopt.BayesSearchCV: returns a fitted optimiser. Hyperparameters and estimators 
            can be extracted using the best_params_() and best_estimator_() method
        """

        param_space = {
            'n_estimators': Integer(100, 1000),
            'max_depth': Integer(3, 13),
            'learning_rate': Real(0.01, 1.0),
            'gamma': Real(0, 5.0),
            'subsample': Real(0.5, 1),
        }

        optimiser = BayesSearchCV(XGBRegressor(),
                                  param_space,
                                  n_iter=50,
                                  verbose=10
                                  )
        
        optimiser.fit(X, y)

        return optimiser
    



class ARIMATuner(HyperparameterTuner):
    """
    Concrete class representing an object that tunes ARIMA hyperparameters:
    parameters p and q, and the unit root term d
    """
    def __init__(self):
        super().__init__()

    def _aic_arima_model(self, p, q, d, train):
        """
        Calculates the Akaike Information Criterion (AIC) of an ARIMA(p,q,d) model

        Returns:
            float: the AIC of an ARIMA(p,q,d) model
        """
        cfg = (p, q, d)
        model = ARIMA(train, order=cfg)
        model_fit = model.fit()

        return model_fit.aic

    def _bic_arima_model(self, p, q, d, train):
        """
        Calculates the Bayesian Information Criterion (BIC) of an ARIMA(p,q,d) model.

        Returns:
            float: the BIC of an ARIMA(p,q,d) model
        """
        cfg = (p, q, d)
        model = ARIMA(train, order=cfg)
        model_fit = model.fit()

        return model_fit.bic
    
    def _bse_arima_model(self, p, q, d, train):
        cfg = (p, q, d)
        model = ARIMA(train, order=cfg)
        model_fit = model.fit()

        return model_fit.bse[1]
    
    def _find_d_values(self, train):
        """
        Finds order of differencing for time series data.

        Returns: 
            list<int>: orders of differencing
        """
        d_values = []
        if self.is_stationary(train):
            return 0
        else:
            #  start with first order difference of time series
            i = 1
            #  continue taking higher order differences until stationary
            while self.is_stationary(self._y_train.shift(i)) is False:
                d_values.append(i)
                i += 1
        return d_values

    def grid_search(self, param_space, method, train):
        """
        Tunes ARIMA hyperparameters by performing a grid search, using 
        Akaike Information Criterion (AIC) or Bayesian Information Criterion (BIC)
        as the scoring function.

        Params:
            dict<str: list<int>>: dictionary object with keys given by strings, 
            which must be labelled 'p', 'q', and 'd', with values given by 
            lists of integers. I.e. {'p': [1,2,3,4], 'q': [1,2,3,4], 'd': [1,2]}
        
        Returns:
            tuple: the hyperparmeters p, q, and d
        """
        best_score = float('inf') 
        score = None
        best_cfg = None

        #  the p and q hyperparameters are given by statistically significant 
        #  lags on the autocorrelation plot
        p_values = param_space['p']
        q_values = param_space['q']
        d_values = param_space['d']

        for p in p_values:
            for q in q_values:
                for d in d_values:
                    cfg = (p, q, d)
                    if method == 'aic':
                        score = self._aic_arima_model(p, q, d, train)
                    elif method == 'bic':
                        score = self._bic_arima_model(p, q, d, train)
                    elif method == 'bse':
                        score = self._bse_arima_model(p, q, d, train)
                    print(f'{method.upper()} score = {score}, cfg = {cfg}')
                    if score < best_score:
                        best_score = score
                        best_cfg = cfg 
        model = ARIMAEstimator(train, order=best_cfg)
        return best_cfg, model


class GARCHTuner(HyperparameterTuner):
    """
    Concrete class representing an object that tunes the hyperparameters of a 
    GARCH model.
    """
    def __init__(self, df, target):
        super().__init__(df, target)

    def grid_search(self, p_values, q_values):
        raise NotImplementedError
        best_p, best_q = None, None
        model = GARCHEstimator(self.get_y_train(), p=best_p, q=best_q)
        return model