"""
Forecast Engine
Advanced time series forecasting for financial markets with multiple models and ensemble methods.
"""

import asyncio
import logging
import numpy as np
from typing import Dict, Any, Optional, List, Tuple, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from collections import defaultdict

logger = logging.getLogger(__name__)


class ForecastModel(str, Enum):
    """Supported forecasting models."""
    ARIMA = "arima"
    SARIMA = "sarima"
    PROPHET = "prophet"
    LSTM = "lstm"
    TRANSFORMER = "transformer"
    GRU = "gru"
    XGBOOST = "xgboost"
    LIGHTGBM = "lightgbm"
    RANDOM_FOREST = "random_forest"
    LINEAR = "linear"
    ELASTIC_NET = "elastic_net"
    ENSEMBLE = "ensemble"


class ForecastHorizon(str, Enum):
    """Forecast horizons."""
    INTRADAY = "intraday"      # Minutes to hours
    DAILY = "daily"            # 1-30 days
    WEEKLY = "weekly"          # 1-12 weeks
    MONTHLY = "monthly"        # 1-12 months
    QUARTERLY = "quarterly"    # 1-4 quarters
    ANNUAL = "annual"          # 1-5 years


@dataclass
class ForecastConfig:
    """Configuration for forecast engine."""
    model: ForecastModel = ForecastModel.ENSEMBLE
    horizon: ForecastHorizon = ForecastHorizon.DAILY
    forecast_steps: int = 30
    confidence_levels: List[float] = field(default_factory=lambda: [0.80, 0.90, 0.95, 0.99])
    retrain_frequency: int = 30  # Days
    validation_window: int = 252  # Days
    feature_window: int = 60  # Days for feature engineering
    ensemble_weights: Optional[Dict[str, float]] = None
    use_exogenous: bool = True
    handle_missing: str = "interpolate"  # interpolate, forward_fill, drop


@dataclass
class ForecastResult:
    """Result of a forecast."""
    symbol: str
    model: ForecastModel
    horizon: ForecastHorizon
    timestamps: List[datetime]
    point_forecast: np.ndarray
    lower_bounds: Dict[float, np.ndarray]  # confidence -> array
    upper_bounds: Dict[float, np.ndarray]
    metrics: Dict[str, float]  # MAE, RMSE, MAPE, etc.
    feature_importance: Optional[Dict[str, float]] = None
    residuals: Optional[np.ndarray] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    generated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class BacktestResult:
    """Result of model backtesting."""
    model: ForecastModel
    symbol: str
    period: Tuple[datetime, datetime]
    metrics: Dict[str, float]
    predictions: np.ndarray
    actuals: np.ndarray
    residuals: np.ndarray
    hit_rate: float  # Directional accuracy


class ForecastEngine:
    """
    Advanced forecasting engine supporting multiple models and ensemble methods.
    Features:
    - Multiple model families (statistical, ML, deep learning)
    - Ensemble forecasting with dynamic weighting
    - Automated feature engineering
    - Cross-validation and backtesting
    - Model selection and hyperparameter tuning
    - Prediction intervals
    """
    
    def __init__(self, config: Optional[ForecastConfig] = None):
        self.config = config or ForecastConfig()
        self._models: Dict[str, Any] = {}
        self._fitted_models: Dict[str, Any] = {}
        self._feature_cache: Dict[str, np.ndarray] = {}
        self._scalers: Dict[str, Any] = {}
        self._performance_history: Dict[str, List[BacktestResult]] = defaultdict(list)
    
    async def initialize(self) -> None:
        """Initialize the forecast engine."""
        logger.info("Forecast engine initialized")
    
    def _create_features(
        self,
        data: np.ndarray,
        timestamps: List[datetime],
        exogenous: Optional[Dict[str, np.ndarray]] = None
    ) -> np.ndarray:
        """Create features for forecasting."""
        n = len(data)
        features = []
        
        # Lag features
        for lag in [1, 2, 3, 5, 10, 20, 60]:
            if n > lag:
                lagged = np.roll(data, lag)
                lagged[:lag] = np.nan
                features.append(lagged)
        
        # Rolling statistics
        for window in [5, 10, 20, 60]:
            if n >= window:
                roll_mean = np.convolve(data, np.ones(window)/window, mode='full')[:n]
                roll_std = np.array([np.std(data[max(0,i-window):i+1]) if i >= window else np.nan for i in range(n)])
                features.append(roll_mean)
                features.append(roll_std)
        
        # Returns
        returns = np.diff(data, prepend=data[0]) / data
        features.append(returns)
        
        # Log returns
        log_returns = np.diff(np.log(data + 1e-10), prepend=np.log(data[0] + 1e-10))
        features.append(log_returns)
        
        # Momentum
        for period in [5, 10, 20, 60]:
            if n > period:
                momentum = data / np.roll(data, period) - 1
                momentum[:period] = np.nan
                features.append(momentum)
        
        # Technical indicators
        # RSI
        if n >= 14:
            delta = np.diff(data, prepend=data[0])
            gain = np.where(delta > 0, delta, 0)
            loss = np.where(delta < 0, -delta, 0)
            avg_gain = np.convolve(gain, np.ones(14)/14, mode='full')[:n]
            avg_loss = np.convolve(loss, np.ones(14)/14, mode='full')[:n]
            rs = avg_gain / (avg_loss + 1e-10)
            rsi = 100 - 100 / (1 + rs)
            features.append(rsi)
        
        # MACD
        if n >= 26:
            ema12 = self._ema(data, 12)
            ema26 = self._ema(data, 26)
            macd = ema12 - ema26
            signal = self._ema(macd, 9)
            features.append(macd)
            features.append(signal)
            features.append(macd - signal)
        
        # Exogenous variables
        if exogenous:
            for name, values in exogenous.items():
                if len(values) == n:
                    features.append(values)
        
        # Time features
        if timestamps:
            hours = np.array([t.hour for t in timestamps])
            days = np.array([t.weekday() for t in timestamps])
            months = np.array([t.month for t in timestamps])
            features.append(hours / 23.0)
            features.append(days / 6.0)
            features.append((months - 1) / 11.0)
        
        # Stack features
        feature_matrix = np.column_stack(features)
        
        # Handle NaN
        if self.config.handle_missing == "interpolate":
            for i in range(feature_matrix.shape[1]):
                col = feature_matrix[:, i]
                nan_mask = np.isnan(col)
                if np.any(nan_mask) and not np.all(nan_mask):
                    col[nan_mask] = np.interp(
                        np.flatnonzero(nan_mask),
                        np.flatnonzero(~nan_mask),
                        col[~nan_mask]
                    )
        elif self.config.handle_missing == "forward_fill":
            for i in range(feature_matrix.shape[1]):
                col = feature_matrix[:, i]
                mask = np.isnan(col)
                idx = np.where(~mask, np.arange(len(mask)), 0)
                np.maximum.accumulate(idx, out=idx)
                col[mask] = col[idx[mask]]
        
        return feature_matrix
    
    def _ema(self, data: np.ndarray, period: int) -> np.ndarray:
        """Exponential moving average."""
        alpha = 2 / (period + 1)
        ema = np.zeros_like(data)
        ema[0] = data[0]
        for i in range(1, len(data)):
            ema[i] = alpha * data[i] + (1 - alpha) * ema[i-1]
        return ema
    
    async def fit(
        self,
        symbol: str,
        data: np.ndarray,
        timestamps: List[datetime],
        exogenous: Optional[Dict[str, np.ndarray]] = None,
        model: Optional[ForecastModel] = None
    ) -> Dict[str, Any]:
        """Fit forecasting model(s) to data."""
        model = model or self.config.model
        
        # Create features
        features = self._create_features(data, timestamps, exogenous)
        
        # Prepare target
        target = data[self.config.feature_window:]  # Skip initial window for features
        feature_matrix = features[self.config.feature_window:]
        
        # Remove rows with NaN
        valid_mask = ~np.any(np.isnan(feature_matrix), axis=1) & ~np.isnan(target)
        X = feature_matrix[valid_mask]
        y = target[valid_mask]
        
        if len(X) < 50:
            raise ValueError(f"Insufficient data for training: {len(X)} samples")
        
        # Train model
        if model == ForecastModel.ENSEMBLE:
            results = await self._fit_ensemble(symbol, X, y, data, timestamps, exogenous)
        elif model == ForecastModel.ARIMA:
            results = await self._fit_arima(symbol, data)
        elif model == ForecastModel.PROPHET:
            results = await self._fit_prophet(symbol, data, timestamps)
        elif model == ForecastModel.LSTM:
            results = await self._fit_lstm(symbol, X, y)
        elif model == ForecastModel.XGBOOST:
            results = await self._fit_xgboost(symbol, X, y)
        elif model == ForecastModel.LIGHTGBM:
            results = await self._fit_lightgbm(symbol, X, y)
        elif model == ForecastModel.LINEAR:
            results = await self._fit_linear(symbol, X, y)
        else:
            raise NotImplementedError(f"Model {model} not implemented")
        
        self._fitted_models[symbol] = results
        return results
    
    async def _fit_ensemble(
        self,
        symbol: str,
        X: np.ndarray,
        y: np.ndarray,
        data: np.ndarray,
        timestamps: List[datetime],
        exogenous: Optional[Dict[str, np.ndarray]]
    ) -> Dict[str, Any]:
        """Fit ensemble of models."""
        weights = self.config.ensemble_weights or {
            "linear": 0.2,
            "xgboost": 0.3,
            "lightgbm": 0.3,
            "arima": 0.2
        }
        
        models = {}
        for name, weight in weights.items():
            if name == "linear":
                models[name] = await self._fit_linear(symbol, X, y)
            elif name == "xgboost":
                models[name] = await self._fit_xgboost(symbol, X, y)
            elif name == "lightgbm":
                models[name] = await self._fit_lightgbm(symbol, X, y)
            elif name == "arima":
                models[name] = await self._fit_arima(symbol, data)
        
        return {
            "type": "ensemble",
            "models": models,
            "weights": weights
        }
    
    async def _fit_linear(self, symbol: str, X: np.ndarray, y: np.ndarray) -> Dict[str, Any]:
        """Fit linear regression model."""
        from sklearn.linear_model import RidgeCV
        from sklearn.preprocessing import StandardScaler
        
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)
        
        model = RidgeCV(alphas=np.logspace(-3, 3, 10))
        model.fit(X_scaled, y)
        
        return {
            "type": "linear",
            "model": model,
            "scaler": scaler,
            "feature_names": [f"f{i}" for i in range(X.shape[1])]
        }
    
    async def _fit_xgboost(self, symbol: str, X: np.ndarray, y: np.ndarray) -> Dict[str, Any]:
        """Fit XGBoost model."""
        try:
            import xgboost as xgb
        except ImportError:
            raise RuntimeError("xgboost not installed. Install with: pip install xgboost")
        
        dtrain = xgb.DMatrix(X, label=y)
        params = {
            "objective": "reg:squarederror",
            "max_depth": 5,
            "learning_rate": 0.1,
            "n_estimators": 100,
            "subsample": 0.8,
            "colsample_bytree": 0.8
        }
        
        model = xgb.train(params, dtrain, num_boost_round=100)
        
        return {
            "type": "xgboost",
            "model": model,
            "params": params
        }
    
    async def _fit_lightgbm(self, symbol: str, X: np.ndarray, y: np.ndarray) -> Dict[str, Any]:
        """Fit LightGBM model."""
        try:
            import lightgbm as lgb
        except ImportError:
            raise RuntimeError("lightgbm not installed. Install with: pip install lightgbm")
        
        train_data = lgb.Dataset(X, label=y)
        params = {
            "objective": "regression",
            "metric": "rmse",
            "num_leaves": 31,
            "learning_rate": 0.1,
            "n_estimators": 100
        }
        
        model = lgb.train(params, train_data, num_boost_round=100)
        
        return {
            "type": "lightgbm",
            "model": model,
            "params": params
        }
    
    async def _fit_arima(self, symbol: str, data: np.ndarray) -> Dict[str, Any]:
        """Fit ARIMA model."""
        try:
            from statsmodels.tsa.arima.model import ARIMA
        except ImportError:
            raise RuntimeError("statsmodels not installed. Install with: pip install statsmodels")
        
        # Auto ARIMA selection (simplified)
        best_aic = np.inf
        best_model = None
        best_order = None
        
        for p in range(3):
            for d in range(2):
                for q in range(3):
                    try:
                        model = ARIMA(data, order=(p, d, q))
                        fitted = model.fit()
                        if fitted.aic < best_aic:
                            best_aic = fitted.aic
                            best_model = fitted
                            best_order = (p, d, q)
                    except Exception:
                        continue
        
        return {
            "type": "arima",
            "model": best_model,
            "order": best_order,
            "aic": best_aic
        }
    
    async def _fit_prophet(
        self,
        symbol: str,
        data: np.ndarray,
        timestamps: List[datetime]
    ) -> Dict[str, Any]:
        """Fit Prophet model."""
        try:
            from prophet import Prophet
        except ImportError:
            raise RuntimeError("prophet not installed. Install with: pip install prophet")
        
        df = pd.DataFrame({
            "ds": timestamps,
            "y": data
        })
        
        model = Prophet(
            yearly_seasonality=True,
            weekly_seasonality=True,
            daily_seasonality=False,
            changepoint_prior_scale=0.05
        )
        model.fit(df)
        
        return {
            "type": "prophet",
            "model": model
        }
    
    async def _fit_lstm(self, symbol: str, X: np.ndarray, y: np.ndarray) -> Dict[str, Any]:
        """Fit LSTM model."""
        try:
            import torch
            import torch.nn as nn
        except ImportError:
            raise RuntimeError("torch not installed. Install with: pip install torch")
        
        # Simple LSTM implementation
        class LSTMModel(nn.Module):
            def __init__(self, input_size, hidden_size=64, num_layers=2):
                super().__init__()
                self.lstm = nn.LSTM(input_size, hidden_size, num_layers, batch_first=True)
                self.fc = nn.Linear(hidden_size, 1)
            
            def forward(self, x):
                out, _ = self.lstm(x)
                return self.fc(out[:, -1, :])
        
        # Reshape for LSTM [batch, seq_len, features]
        seq_len = min(30, X.shape[0] // 2)
        X_lstm = X[-seq_len:].reshape(1, seq_len, -1)
        y_lstm = y[-1:].reshape(1, 1)
        
        model = LSTMModel(X.shape[1])
        criterion = nn.MSELoss()
        optimizer = torch.optim.Adam(model.parameters(), lr=0.001)
        
        # Quick training
        for epoch in range(20):
            optimizer.zero_grad()
            output = model(torch.FloatTensor(X_lstm))
            loss = criterion(output, torch.FloatTensor(y_lstm))
            loss.backward()
            optimizer.step()
        
        return {
            "type": "lstm",
            "model": model,
            "seq_len": seq_len
        }
    
    async def predict(
        self,
        symbol: str,
        steps: Optional[int] = None,
        exogenous: Optional[Dict[str, np.ndarray]] = None
    ) -> ForecastResult:
        """Generate forecast for a symbol."""
        if symbol not in self._fitted_models:
            raise ValueError(f"Model not fitted for {symbol}. Call fit() first.")
        
        steps = steps or self.config.forecast_steps
        model_data = self._fitted_models[symbol]
        model_type = model_data.get("type", "unknown")
        
        if model_type == "ensemble":
            return await self._predict_ensemble(symbol, steps, exogenous)
        elif model_type == "linear":
            return await self._predict_linear(symbol, steps, exogenous)
        elif model_type == "xgboost":
            return await self._predict_xgboost(symbol, steps, exogenous)
        elif model_type == "lightgbm":
            return await self._predict_lightgbm(symbol, steps, exogenous)
        elif model_type == "arima":
            return await self._predict_arima(symbol, steps)
        elif model_type == "prophet":
            return await self._predict_prophet(symbol, steps)
        elif model_type == "lstm":
            return await self._predict_lstm(symbol, steps)
        else:
            raise NotImplementedError(f"Prediction not implemented for {model_type}")
    
    async def _predict_ensemble(
        self,
        symbol: str,
        steps: int,
        exogenous: Optional[Dict[str, np.ndarray]]
    ) -> ForecastResult:
        """Generate ensemble predictions."""
        model_data = self._fitted_models[symbol]
        models = model_data["models"]
        weights = model_data["weights"]
        
        predictions = {}
        for name, model in models.items():
            # Get prediction from each model
            if model["type"] == "linear":
                pred = await self._predict_from_linear(model, steps, exogenous)
            elif model["type"] == "xgboost":
                pred = await self._predict_from_xgboost(model, steps, exogenous)
            elif model["type"] == "lightgbm":
                pred = await self._predict_from_lightgbm(model, steps, exogenous)
            elif model["type"] == "arima":
                pred = await self._predict_from_arima(model, steps)
            else:
                continue
            predictions[name] = pred
        
        # Weighted ensemble
        point_forecast = np.zeros(steps)
        for name, pred in predictions.items():
            point_forecast += weights.get(name, 0) * pred
        
        # Estimate uncertainty from ensemble spread
        preds_array = np.array(list(predictions.values()))
        std_forecast = np.std(preds_array, axis=0)
        
        # Confidence intervals
        lower_bounds = {}
        upper_bounds = {}
        for cl in self.config.confidence_levels:
            z = norm.ppf((1 + cl) / 2)
            lower_bounds[cl] = point_forecast - z * std_forecast
            upper_bounds[cl] = point_forecast + z * std_forecast
        
        return ForecastResult(
            symbol=symbol,
            model=ForecastModel.ENSEMBLE,
            horizon=self.config.horizon,
            timestamps=[datetime.utcnow() + timedelta(days=i+1) for i in range(steps)],
            point_forecast=point_forecast,
            lower_bounds=lower_bounds,
            upper_bounds=upper_bounds,
            metrics={"ensemble_std": float(np.mean(std_forecast))}
        )
    
    async def _predict_linear(
        self,
        symbol: str,
        steps: int,
        exogenous: Optional[Dict[str, np.ndarray]]
    ) -> ForecastResult:
        """Predict using linear model."""
        # Simplified - would use actual model
        return ForecastResult(
            symbol=symbol,
            model=ForecastModel.LINEAR,
            horizon=self.config.horizon,
            timestamps=[datetime.utcnow() + timedelta(days=i+1) for i in range(steps)],
            point_forecast=np.zeros(steps),
            lower_bounds={cl: np.zeros(steps) for cl in self.config.confidence_levels},
            upper_bounds={cl: np.zeros(steps) for cl in self.config.confidence_levels},
            metrics={}
        )
    
    # Additional predict methods would follow similar patterns
    # ... (abbreviated for brevity)
    
    async def backtest(
        self,
        symbol: str,
        data: np.ndarray,
        timestamps: List[datetime],
        test_size: int = 60,
        model: Optional[ForecastModel] = None
    ) -> BacktestResult:
        """Backtest model on historical data."""
        model = model or self.config.model
        
        train_data = data[:-test_size]
        train_timestamps = timestamps[:-test_size]
        test_data = data[-test_size:]
        test_timestamps = timestamps[-test_size:]
        
        # Fit on training data
        await self.fit(symbol, train_data, train_timestamps, model=model)
        
        # Predict
        result = await self.predict(symbol, test_size)
        
        # Calculate metrics
        predictions = result.point_forecast
        actuals = test_data
        
        mae = np.mean(np.abs(predictions - actuals))
        rmse = np.sqrt(np.mean((predictions - actuals)**2))
        mape = np.mean(np.abs((actuals - predictions) / (actuals + 1e-10))) * 100
        
        # Directional accuracy
        pred_dir = np.diff(predictions, prepend=actuals[0])
        actual_dir = np.diff(actuals, prepend=actuals[0])
        hit_rate = np.mean((pred_dir > 0) == (actual_dir > 0))
        
        return BacktestResult(
            model=model,
            symbol=symbol,
            period=(test_timestamps[0], test_timestamps[-1]),
            metrics={"mae": mae, "rmse": rmse, "mape": mape, "hit_rate": hit_rate},
            predictions=predictions,
            actuals=actuals,
            residuals=predictions - actuals,
            hit_rate=hit_rate
        )
    
    def get_stats(self) -> Dict[str, Any]:
        return {
            "fitted_models": len(self._fitted_models),
            "model_types": list(set(m.get("type", "unknown") for m in self._fitted_models.values())),
            "performance_history": {k: len(v) for k, v in self._performance_history.items()}
        }


# Global forecast engine instance
_forecast_engine: Optional[ForecastEngine] = None


def get_forecast_engine(config: Optional[ForecastConfig] = None) -> ForecastEngine:
    global _forecast_engine
    if _forecast_engine is None:
        _forecast_engine = ForecastEngine(config)
    return _forecast_engine


async def close_forecast_engine() -> None:
    global _forecast_engine
    if _forecast_engine:
        _forecast_engine = None