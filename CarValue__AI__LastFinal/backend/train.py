from pathlib import Path
import json, pickle, pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.ensemble import ExtraTreesRegressor, RandomForestRegressor, GradientBoostingRegressor
from sklearn.linear_model import LinearRegression, Ridge

def main():
    BASE = Path(__file__).resolve().parents[1]
    df = pd.read_csv(BASE / "data/used_cars_cleaned.csv")
    features = ["Brand", "Model", "Location", "Year", "Kilometers_Driven", "Fuel_Type", "Transmission", "Owner_Type", "Mileage", "Engine", "Power", "Seats"]
    X = df[features]
    y = df["Price_Lakhs"]
    
    cat = ["Brand", "Model", "Location", "Fuel_Type", "Transmission", "Owner_Type"]
    num = ["Year", "Kilometers_Driven", "Mileage", "Engine", "Power", "Seats"]
    
    prep = ColumnTransformer([
        ("num", Pipeline([("imp", SimpleImputer(strategy="median"))]), num),
        ("cat", Pipeline([("imp", SimpleImputer(strategy="most_frequent")), ("ohe", OneHotEncoder(handle_unknown="ignore"))]), cat)
    ])
    
    models = {
        "Linear Regression": LinearRegression(),
        "Ridge Regression": Ridge(alpha=10),
        "Random Forest": RandomForestRegressor(n_estimators=150, random_state=42, n_jobs=-1),
        "Gradient Boosting": GradientBoostingRegressor(n_estimators=100, learning_rate=0.08, max_depth=3, random_state=42),
        "Extra Trees": ExtraTreesRegressor(n_estimators=150, random_state=42, n_jobs=-1)
    }
    
    xt, xv, yt, yv = train_test_split(X, y, test_size=0.2, random_state=42)
    results = []
    
    print(f"Training models on {len(df)} rows across {df['Brand'].nunique()} brands and {df['Model'].nunique()} models...", flush=True)
    for name, m in models.items():
        print(f"  Training {name}...", flush=True)
        pipe = Pipeline([("prep", prep), ("model", m)])
        pipe.fit(xt, yt)
        pred = pipe.predict(xv)
        mae = float(mean_absolute_error(yv, pred))
        rmse = float(mean_squared_error(yv, pred)**0.5)
        r2 = float(r2_score(yv, pred))
        results.append({"model": name, "mae": mae, "rmse": rmse, "r2": r2})
        print(f"    -> MAE: {mae:.3f}, RMSE: {rmse:.3f}, R2: {r2:.4f}", flush=True)
        
    results.sort(key=lambda x: x["r2"], reverse=True)
    best_name = results[0]["model"]
    print(f"\nBest Model: {best_name} with R2 = {results[0]['r2']:.4f}", flush=True)
    
    print(f"Fitting best model {best_name} on entire dataset...", flush=True)
    best = Pipeline([("prep", prep), ("model", models[best_name])])
    best.fit(X, y)
    
    with open(BASE / "models/car_price_model.pkl", "wb") as f:
        pickle.dump(best, f)
        
    meta = {
        "dataset_rows": len(df),
        "target": "Price_Lakhs",
        "features": features,
        "model_comparison": results,
        "best": {"best_model": best_name, "metrics": results[0]}
    }
    (BASE / "models/metrics.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print("Saved model to models/car_price_model.pkl and metrics to models/metrics.json successfully!", flush=True)

if __name__ == "__main__":
    main()
