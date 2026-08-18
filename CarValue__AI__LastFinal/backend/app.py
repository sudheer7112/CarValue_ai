from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from pathlib import Path
import pickle, json, math
import pandas as pd

BASE = Path(__file__).resolve().parents[1]
FRONTEND = BASE / "frontend"

# Load models and catalog data
with open(BASE / "models" / "car_price_model.pkl", "rb") as f:
    MODEL = pickle.load(f)
META = json.loads((BASE / "models" / "metrics.json").read_text(encoding="utf-8"))
CATALOG = json.loads((BASE / "data" / "catalog.json").read_text(encoding="utf-8"))
DATA = pd.read_csv(BASE / "data" / "used_cars_cleaned.csv")

app = Flask(__name__)
CORS(app)

def num(v, default=0):
    try: return float(v)
    except: return float(default)

def owner(v):
    return {"First Owner":"First","Second Owner":"Second","Third Owner":"Third",
            "Fourth & Above Owner":"Fourth & Above"}.get(str(v).strip(), str(v or "First"))

def normalize_brand(b):
    b = str(b or "").strip()
    b_lower = b.lower()
    if b_lower in ("maruti", "maruti suzuki", "marutisuzuki"):
        return "Maruti Suzuki"
    if b_lower in ("land", "land rover", "landrover"):
        return "Land Rover"
    if b_lower in ("range", "range rover", "rangerover"):
        return "Range Rover"
    if b_lower in ("citroen", "citroën", "citroen india"):
        return "Citroën"
    if b_lower in ("mercedes", "mercedes benz", "mercedes-benz", "benz"):
        return "Mercedes-Benz"
    if b_lower in ("rolls", "rolls royce", "rolls-royce"):
        return "Rolls-Royce"
    if b_lower in ("aston", "aston martin", "astonmartin"):
        return "Aston Martin"
    for cat_b in CATALOG.get("brands", []):
        if cat_b.lower() == b_lower:
            return cat_b
    return b

def specs(brand, model):
    brand = normalize_brand(brand)
    if brand == "Land Rover" and model.startswith("Rover "):
        model = model[6:].strip()
    key = f"{brand}|||{model}"
    if key in CATALOG["specs"]:
        s = CATALOG["specs"][key]
        return {"Engine":s["engine"],"Power":s["power"],"Seats":s["seats"],"Mileage":s["mileage"]}
    rows = DATA[DATA.Brand.eq(brand)]
    if rows.empty: rows = DATA
    return {"Engine":rows.Engine.median(),"Power":rows.Power.median(),
            "Seats":rows.Seats.median(),"Mileage":rows.Mileage.median()}

def normalize(x):
    brand = normalize_brand(x.get("brand") or x.get("Brand") or "Maruti Suzuki")
    model = str(x.get("model") or x.get("Model") or "").strip()
    if brand == "Land Rover" and model.startswith("Rover "):
        model = model[6:].strip()
    s = specs(brand, model)
    key = f"{brand}|||{model}"
    variant = CATALOG.get("variants", {}).get(key, {})
    allowed_fuels = variant.get("fuel_types", CATALOG.get("fuel_types", []))
    allowed_transmissions = variant.get("transmissions", CATALOG.get("transmissions", []))
    selected_fuel = str(x.get("fuel") or x.get("Fuel_Type") or (allowed_fuels[0] if allowed_fuels else "Petrol")).strip()
    selected_trans = str(x.get("transmission") or x.get("Transmission") or (allowed_transmissions[0] if allowed_transmissions else "Manual")).strip()
    if selected_fuel not in allowed_fuels:
        msg = (f"{brand} {model} is not listed with {selected_fuel} fuel "
               f"in the available records.")
        raise ValueError(msg)
    if selected_trans not in allowed_transmissions:
        msg = (f"{brand} {model} is not listed with {selected_trans} "
               f"transmission in the available records.")
        raise ValueError(msg)
    mileage = num(x.get("mileage") or x.get("Mileage"), s["Mileage"])
    if mileage <= 0 or mileage >= 30:
        raise ValueError("Mileage must be below 30 km/l.")
    year = int(num(x.get("year") or x.get("Year"), 2022))
    if year < 1998 or year > 2026:
        raise ValueError("Year must be between 1998 and 2026.")
    
    battery_capacity = num(x.get("battery_capacity") or x.get("battery_kwh") or x.get("Battery_Capacity"), 0)
    if selected_fuel == "Electric" and battery_capacity <= 0:
        m_lower = model.lower()
        if "sierra" in m_lower or "curvv" in m_lower: battery_capacity = 55.0
        elif "nexon" in m_lower: battery_capacity = 40.5
        elif "punch" in m_lower: battery_capacity = 35.0
        elif "tiago" in m_lower or "tigor" in m_lower: battery_capacity = 24.0
        elif "zs" in m_lower or "mg" in brand.lower(): battery_capacity = 50.3
        elif "atto" in m_lower or "seal" in m_lower or "byd" in brand.lower(): battery_capacity = 60.4
        elif "ioniq" in m_lower or "ev6" in m_lower: battery_capacity = 72.6
        else: battery_capacity = 40.0

    return {
        "Brand":brand, "Model":model,
        "Location":str(x.get("location") or x.get("Location") or "Mumbai").strip(),
        "Year":year,
        "Kilometers_Driven":num(x.get("km_driven") or x.get("Kilometers_Driven"), 45000),
        "Fuel_Type":selected_fuel,
        "Transmission":selected_trans,
        "Owner_Type":owner(x.get("owner") or x.get("Owner_Type")),
        "Mileage":mileage,
        "Engine":s["Engine"], "Power":s["Power"], "Seats":s["Seats"],
        "Battery_Capacity": round(battery_capacity, 1)
    }

def signals(p):
    age=max(0,2026-int(p["Year"])); km=float(p["Kilometers_Driven"]); mi=float(p["Mileage"])
    age_s=max(0,min(100,100-age*7))
    usage=max(0,min(100,100-km/180000*100))
    mileage=max(0,min(100,(mi-8)/20*100))
    own={"First":100,"Second":82,"Third":64,"Fourth & Above":46}.get(p["Owner_Type"],60)
    efficiency=max(0,min(100,mi/25*100))
    flags=[]
    
    ev_analysis = None
    if p["Fuel_Type"] == "Electric":
        kwh = float(p.get("Battery_Capacity", 40.0))
        eff = mi if (mi >= 4.0 and mi <= 14.0) else 7.5
        base_range = round(kwh * eff, 1)
        est_soh = max(75.0, round(100.0 - age * 1.8 - (km / 100000.0) * 3.5, 1))
        real_world_range = round(base_range * (est_soh / 100.0), 1)
        ev_cost_per_km = round(8.0 / max(1.0, eff), 2)
        ice_cost_per_km = round(100.0 / 15.0, 2)
        annual_savings = round((ice_cost_per_km - ev_cost_per_km) * 120, 0)
        
        health_label = "Healthy Battery Pack" if est_soh >= 90 else ("Moderate Degradation" if est_soh >= 82 else "High Degradation - Diagnostics Needed")
        ev_analysis = {
            "battery_capacity_kwh": kwh,
            "estimated_soh_percent": est_soh,
            "real_world_range_km": real_world_range,
            "cost_per_km_rs": ev_cost_per_km,
            "annual_fuel_savings_thousands_rs": max(10, annual_savings),
            "health_verdict": health_label
        }
        flags.append(f"EV Battery Analysis ({kwh} kWh pack): Est. Battery Health (SOH) is {est_soh}%. Real-world range ~{real_world_range} km.")
    else:
        if age>=8: flags.append("Older vehicle — inspect suspension, seals and cooling system.")
        if km>=100000: flags.append("High odometer — verify service history and major replacements.")
        if mi<12: flags.append("Lower efficiency — check whether running cost fits your usage.")
        if p["Owner_Type"] in {"Third","Fourth & Above"}: flags.append("Multiple owners — verify ownership and service records carefully.")
        if not flags: flags.append("No major warning from the supplied fields; physical inspection is still essential.")

    return {"age":round(age_s),"usage":round(usage),"mileage":round(mileage),
            "ownership":round(own),"efficiency":round(efficiency),
            "vehicle_age":age,"flags":flags,"ev_analysis":ev_analysis}

def decision(s):
    value = (s["age"] * 0.24 + s["usage"] * 0.24 + s["mileage"] * 0.16 + 
             s["ownership"] * 0.16 + s["efficiency"] * 0.20)
    if value >= 80:
        return {"label": "Strong candidate", "tone": "good",
                "action": "Proceed if inspection and asking price check out."}
    if value >= 65:
        return {"label": "Worth considering", "tone": "fair",
                "action": "Inspect it and negotiate around the fair-value band."}
    if value >= 50:
        return {"label": "Inspect before buying", "tone": "warn",
                "action": "Do not rush; verify history, condition and seller claims."}
    return {"label": "Proceed with caution", "tone": "bad",
            "action": "Only continue if the price compensates for the visible risks."}

def money_plan(p):
    return {"opening_offer":round(p*.92,2),"target_price":round(p*.97,2),
            "upper_fair_price":round(p*1.03,2),
            "tip":"Start below fair value and move toward the target only when inspection is clean."}

def depreciation(p, age):
    rate=.07 if age<8 else .06
    return [{"year":1,"value":round(p*(1-rate),2)},
            {"year":3,"value":round(p*(1-rate)**3,2)},
            {"year":5,"value":round(p*(1-rate)**5,2)}]

def predict_one(payload):
    p=normalize(payload)
    pred=max(.05,float(MODEL.predict(pd.DataFrame([p]))[0]))
    mae=float(META["best"]["metrics"]["mae"]); band=max(.15,mae*.85)
    s=signals(p)
    return {"input":p,"predicted_price_lakhs":round(pred,2),
            "price_range_lakhs":[round(max(0,pred-band),2),round(pred+band,2)],
            "decision":decision(s),"signals":s,
            "depreciation":depreciation(pred,s["vehicle_age"]),
            "negotiation":money_plan(pred),
            "ev_analysis":s.get("ev_analysis"),
            "specs":{"engine_cc":round(p["Engine"]),"power_bhp":round(p["Power"],1),
                     "seats":round(p["Seats"]),"mileage":round(p["Mileage"],1),
                     "battery_kwh":round(p.get("Battery_Capacity", 0), 1)}}

@app.get("/")
def home(): return send_from_directory(FRONTEND,"index.html")

@app.get("/<path:filename>")
def files(filename): return send_from_directory(FRONTEND,filename)

@app.get("/api/catalog")
def catalog(): return jsonify(CATALOG)

@app.get("/api/health")
def health(): return jsonify({"status":"ok"})

@app.post("/api/predict")
def predict():
    try: return jsonify(predict_one(request.get_json(force=True)))
    except Exception as e: return jsonify({"error":str(e)}),400

@app.post("/api/compare")
def compare():
    try:
        b=request.get_json(force=True)
        a=predict_one(b.get("carA",{})); c=predict_one(b.get("carB",{}))
        def rank(x):
            s=x["signals"]
            return s["age"]*.20+s["usage"]*.20+s["mileage"]*.15+s["ownership"]*.15+s["efficiency"]*.15
        ra,rb=rank(a),rank(c)
        winner="Very close — choose the better inspected example." if abs(ra-rb)<3 else ("Car A" if ra>rb else "Car B")
        return jsonify({"carA":a,"carB":c,"winner":winner})
    except Exception as e: return jsonify({"error":str(e)}),400

@app.post("/api/recommendations")
def recommendations():
    try:
        p=normalize(request.get_json(force=True))
        p_res = predict_one(p)
        p_pred = p_res["predicted_price_lakhs"]
        
        stats=DATA.groupby(["Brand","Model"],as_index=False).agg(
            Engine=("Engine","median"),Power=("Power","median"),Seats=("Seats","median"),
            Mileage=("Mileage","median"),Sample_Size=("Price_Lakhs","size"),
            Year_Min=("Year","min"),Year_Max=("Year","max"))
        
        scored = []
        for r in stats.itertuples(index=False):
            if r.Brand==p["Brand"] and r.Model==p["Model"]: continue
            key = f"{r.Brand}|||{r.Model}"
            variant = CATALOG.get("variants", {}).get(key, {})
            fuels = variant.get("fuel_types", [])
            transs = variant.get("transmissions", [])
            
            same_fuel = (p["Fuel_Type"] in fuels) if fuels else False
            same_trans = (p["Transmission"] in transs) if transs else False
            same_seats = bool(pd.notna(r.Seats) and round(r.Seats) == round(p["Seats"]))
            
            fuel_score = 14 if same_fuel else 0
            trans_score = 12 if same_trans else 0
            seat_score = 8 if same_seats else 0
            
            eng_gap = abs(float(r.Engine) - float(p["Engine"])) if pd.notna(r.Engine) else 500
            eng_score = max(0, 8 - (eng_gap / 150))
            
            pwr_gap = abs(float(r.Power) - float(p["Power"])) if pd.notna(r.Power) else 30
            pwr_score = max(0, 6 - (pwr_gap / 15))
            
            brand_score = 4 if r.Brand == p["Brand"] else 0
            mid = (r.Year_Min + r.Year_Max) / 2
            gap = min(abs(p["Year"] - r.Year_Min), abs(p["Year"] - r.Year_Max), abs(p["Year"] - mid))
            year_score = max(0, 4 - gap / 3)
            sample_score = min(2, math.log1p(r.Sample_Size) / 3)
            
            match = fuel_score + trans_score + seat_score + eng_score + pwr_score + brand_score + year_score + sample_score
            
            cand_mileage = float(r.Mileage) if pd.notna(r.Mileage) and r.Mileage > 0 else 16.0
            if cand_mileage >= 30:
                cand_mileage = 29.5
            elif cand_mileage <= 0:
                cand_mileage = 15.0
                
            selected_fuel = p["Fuel_Type"] if same_fuel else (fuels[0] if fuels else "Petrol")
            selected_trans = p["Transmission"] if same_trans else (transs[0] if transs else "Manual")
            
            scored.append({
                "match": match,
                "r": r,
                "same_fuel": same_fuel,
                "same_trans": same_trans,
                "same_seats": same_seats,
                "eng_gap": eng_gap,
                "pwr_gap": pwr_gap,
                "fuel": selected_fuel,
                "trans": selected_trans,
                "mileage": cand_mileage
            })
            
        scored.sort(key=lambda x: x["match"], reverse=True)
        
        final = []
        seen = set()
        for item in scored:
            r = item["r"]
            key = f"{r.Brand}|||{r.Model}"
            if key in seen: continue
            seen.add(key)
            
            q = {
                "brand": r.Brand, "model": r.Model, "location": p["Location"], "year": p["Year"],
                "km_driven": p["Kilometers_Driven"], "fuel": item["fuel"],
                "transmission": item["trans"], "owner": p["Owner_Type"], "mileage": item["mileage"]
            }
            try:
                out = predict_one(q)
            except Exception:
                continue
                
            out["match_score"] = round(item["match"], 1)
            out["specs"]["engine_cc"] = round(r.Engine) if pd.notna(r.Engine) else 1200
            out["specs"]["power_bhp"] = round(r.Power, 1) if pd.notna(r.Power) else 75.0
            out["specs"]["seats"] = round(r.Seats) if pd.notna(r.Seats) else 5
            out["specs"]["mileage"] = round(item["mileage"], 1)
            
            price_gap = round(out["predicted_price_lakhs"] - p_pred, 2)
            reasons = []
            badges = []
            if item["same_fuel"]:
                reasons.append(f"Exact fuel match: {p['Fuel_Type']}")
                badges.append(f"{p['Fuel_Type']}")
            if item["same_trans"]:
                reasons.append(f"Exact transmission: {p['Transmission']}")
                badges.append(f"{p['Transmission']}")
            if item["same_seats"]:
                badges.append(f"{round(p['Seats'])} Seats")
            if item["eng_gap"] <= 200 and r.Engine > 0:
                badges.append(f"~{round(r.Engine)} cc Engine")
            elif r.Engine == 0:
                badges.append("Pure EV")
                
            if r.Brand == p["Brand"]:
                reasons.append("Same brand alternative")
            if item["mileage"] > p["Mileage"]:
                reasons.append(f"Higher mileage by {item['mileage']-p['Mileage']:.1f} km/l")
            elif item["mileage"] < p["Mileage"]:
                reasons.append(f"Lower mileage by {p['Mileage']-item['mileage']:.1f} km/l")
            if pd.notna(r.Engine) and r.Engine > 0 and p["Engine"] > 0:
                if r.Engine > p["Engine"]:
                    reasons.append(f"Larger engine: {r.Engine:.0f} cc")
                elif r.Engine < p["Engine"]:
                    reasons.append(f"Smaller engine: {r.Engine:.0f} cc")
            elif r.Engine == 0 and p["Engine"] == 0:
                reasons.append("Zero-emission electric vehicle alternative")
            if not reasons:
                reasons.append("Similar vehicle profile")
            
            out["comparison_to_selected"] = {
                "price_difference_lakhs": price_gap,
                "mileage_difference": round(item["mileage"] - p["Mileage"], 1),
                "engine_difference_cc": round(r.Engine - p["Engine"]) if pd.notna(r.Engine) else 0,
                "power_difference_bhp": round(r.Power - p["Power"], 1) if pd.notna(r.Power) else 0.0,
                "same_fuel": item["same_fuel"],
                "same_transmission": item["same_trans"],
                "same_seats": item["same_seats"],
                "badges": badges,
                "reasons": reasons[:4]
            }
            final.append(out)
            if len(final) == 8:
                break
                
        return jsonify({"recommendations": final})
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.get("/api/metrics")
def metrics():
    return jsonify(json.loads((BASE / "models" / "metrics.json").read_text(encoding="utf-8")))

@app.get("/api/analytics")
def analytics_data():
    try:
        df = DATA.copy()
        df["Car_Age"] = 2026 - df["Year"]
        
        total_records = len(df)
        avg_price = df["Price_Lakhs"].mean()
        median_price = df["Price_Lakhs"].median()
        min_price = df["Price_Lakhs"].min()
        max_price = df["Price_Lakhs"].max()
        
        age_price = df.groupby("Car_Age")["Price_Lakhs"].mean().reset_index()
        age_price_data = [{"age": int(r.Car_Age), "price": float(r.Price_Lakhs)} for _, r in age_price.iterrows()]
        
        bins = [0, 20000, 40000, 60000, 80000, 100000, 125000, 150000, 200000, float('inf')]
        labels = ["0-20k", "20-40k", "40-60k", "60-80k", "80-100k", "100-125k", "125-150k", "150-200k", "200k+"]
        df["km_bins"] = pd.cut(df["Kilometers_Driven"], bins=bins, labels=labels, right=False)
        km_price = df.groupby("km_bins", observed=False)["Price_Lakhs"].mean().reset_index()
        km_price_data = [{"range": str(r.km_bins), "price": float(r.Price_Lakhs) if pd.notna(r.Price_Lakhs) else 0} for _, r in km_price.iterrows()]
        
        brand_price = df.groupby("Brand")["Price_Lakhs"].mean().sort_values(ascending=False).reset_index()
        brand_price_data = [{"brand": str(r.Brand), "price": float(r.Price_Lakhs)} for _, r in brand_price.iterrows()]
        
        fuel_price = df.groupby("Fuel_Type")["Price_Lakhs"].mean().reset_index()
        fuel_price_data = [{"fuel": str(r.Fuel_Type), "price": float(r.Price_Lakhs)} for _, r in fuel_price.iterrows()]
        
        trans_price = df.groupby("Transmission")["Price_Lakhs"].mean().reset_index()
        trans_price_data = [{"transmission": str(r.Transmission), "price": float(r.Price_Lakhs)} for _, r in trans_price.iterrows()]
        
        year_price = df.groupby("Year")["Price_Lakhs"].mean().reset_index()
        year_price_data = [{"year": int(r.Year), "price": float(r.Price_Lakhs)} for _, r in year_price.iterrows()]
        
        cols = ["Engine", "Power", "Mileage", "Car_Age", "Year", "Kilometers_Driven"]
        corr_data = {}
        for c in cols:
            if c in df.columns:
                corr = df[c].corr(df["Price_Lakhs"])
                corr_data[c] = float(corr) if pd.notna(corr) else 0.0
                
        return jsonify({
            "stats": {
                "records": total_records,
                "avg_price": float(avg_price),
                "median_price": float(median_price),
                "min_price": float(min_price),
                "max_price": float(max_price)
            },
            "price_vs_age": age_price_data,
            "price_vs_km": km_price_data,
            "price_by_brand": brand_price_data,
            "price_by_fuel": fuel_price_data,
            "price_by_transmission": trans_price_data,
            "price_trend_year": year_price_data,
            "correlations": corr_data
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 400

if __name__=="__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)

