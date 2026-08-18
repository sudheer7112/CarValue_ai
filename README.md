# CarValue AI

## Problem Statement
Estimating the fair market value of used cars is a complex challenge due to the vast number of variables involved, such as the car's make, model, age, mileage, condition, and underlying market depreciation trends. Buyers often lack the transparency needed to make informed decisions, risking overpayment. **CarValue AI** solves this by providing a smart, data-driven web application that instantly predicts fair market used-car prices and provides buyer-centric negotiation signals to empower consumers.

## Features
- **Multi-page Web Application**: Includes Home, Predict, Valuation Result, Compare, Comparison Result, Alternatives, and Analytics pages.
- **Smart Form Validation**: Searchable, compact dropdowns that filter Fuel and Transmission options based on the specific car variant selected.
- **Fair-Value Animation**: Dynamic market-band UI that visually guides the buyer on pricing instead of relying on confusing technical metrics.
- **Side-by-Side Comparison**: Evaluate two different used cars and receive an intelligent verdict on which is the better buy based on condition signals.
- **Smart Alternatives**: Recommends similar cars based on price, mileage, engine displacement, and feature-matching (fuel/transmission/seats).
- **EV Battery Analysis**: For electric vehicles, estimates battery State of Health (SOH), real-world range, cost-per-km, and annual fuel savings versus ICE vehicles.
- **Analytics Dashboard**: Interactive data visualizations covering price trends by brand, fuel type, transmission, year, mileage, and car age — powered by the full dataset.
- **Depreciation Forecast**: Projects the car's estimated value at 1, 3, and 5 years from the present.
- **Negotiation Planner**: Calculates opening offer, target price, and upper fair-value ceiling based on the predicted price.

## Technology Stack
- **Frontend**: HTML5, Vanilla CSS, JavaScript (Dynamic UI, Fetch API)
- **Backend**: Python 3, Flask (RESTful API), Flask-CORS
- **Machine Learning**: Scikit-Learn, Pandas, NumPy (Data processing, pipelines, regression models)

## Dataset
- **Size**: 6,095 cleaned used car records.
- **Coverage**: 38 normalized brands and over 1,800 specific models.
- **Span**: Historical data covering 1998–2019, with conservative year-extension projections mapping up to 2026.
- **Geography**: Prices mapped across 11 major locations in India.

## ML Model
The data pipeline utilizes a `ColumnTransformer` for median numerical imputation and categorical One-Hot Encoding. Five different regression algorithms are evaluated during training:
1. Linear Regression
2. Ridge Regression
3. Random Forest
4. Extra Trees
5. Gradient Boosting **(Current Active Model)**

## How to Install
1. Ensure Python 3.10+ is installed on your system.
2. Open your terminal in the project root directory.
3. Create and activate a virtual environment:
   ```powershell
   python -m venv .venv
   .venv\Scripts\Activate.ps1
   ```
4. Install the required dependencies:
   ```powershell
   python -m pip install -r backend\requirements.txt
   ```

## How to Run
1. With your virtual environment activated, start the Flask web server:
   ```powershell
   python backend\app.py
   ```
2. Flask will display two accessible URLs:
   ```
   * Running on http://127.0.0.1:5000         (localhost)
   * Running on http://<your-network-ip>:5000  (LAN / network)
   ```
3. Open your browser and navigate to `http://127.0.0.1:5000` for local access.

## Project Structure
```
CarValue__AI__Final/
├── backend/
│   ├── app.py              # Flask API server
│   ├── train.py            # Model training script
│   └── requirements.txt    # Python dependencies
├── frontend/
│   ├── index.html          # Home / landing page
│   ├── predict.html        # Car valuation form
│   ├── result.html         # Valuation results page
│   ├── compare.html        # Side-by-side comparison form
│   ├── compare-result.html # Comparison verdict page
│   ├── recommend.html      # Smart alternatives page
│   ├── analytics.html      # Analytics dashboard
│   ├── app.js              # Shared frontend logic
│   └── style.css           # Global stylesheet
├── data/
│   ├── used_cars_cleaned.csv  # Cleaned training dataset
│   └── catalog.json           # Brand/model/variant catalog
├── models/
│   ├── car_price_model.pkl    # Trained ML model
│   └── metrics.json           # Model performance metrics
└── README.md
```

## API Reference
The backend exposes a RESTful JSON API:

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | Serves the main frontend application |
| `GET` | `/api/health` | Health check — returns `{"status": "ok"}` |
| `GET` | `/api/catalog` | Returns all brands, models, variants, and specifications |
| `GET` | `/api/metrics` | Returns model training performance metrics |
| `GET` | `/api/analytics` | Returns aggregated dataset statistics for the analytics dashboard |
| `POST` | `/api/predict` | Accepts car details; returns predicted price, price range, depreciation, buying signals, and EV analysis |
| `POST` | `/api/compare` | Accepts `carA` and `carB`; evaluates and returns the better option |
| `POST` | `/api/recommendations` | Returns top 8 closely matched alternative vehicles |

### Example — `POST /api/predict` Payload
```json
{
  "brand": "Maruti Suzuki",
  "model": "Swift",
  "location": "Mumbai",
  "year": 2020,
  "km_driven": 45000,
  "fuel": "Petrol",
  "transmission": "Manual",
  "owner": "First Owner",
  "mileage": 21.5
}
```

## Results
Based on the holdout test evaluation, the best performing algorithm is the **Gradient Boosting Regressor**, yielding the following benchmarks:
- **R² Score (Accuracy)**: **91.94%** (Variance Explained)
- **Mean Absolute Error (MAE)**: **₹1.95 Lakhs**
- **Root Mean Squared Error (RMSE)**: **₹6.75 Lakhs**
