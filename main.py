from fastapi import FastAPI
import requests

app = FastAPI()

NASA_URL = "https://api.nasa.gov/neo/rest/v1/feed?api_key=DEMO_KEY"


def risk_score(neo):
    try:
        diameter = neo["estimated_diameter"]["meters"]["estimated_diameter_max"]
        hazardous = neo["is_potentially_hazardous_asteroid"]
        miss = float(
            neo["close_approach_data"][0]["miss_distance"]["kilometers"]
        )

        score = 0
        if hazardous:
            score += 50
        score += min(diameter / 10, 30)
        score += max(0, 20 - (miss / 1_000_000))

        return round(score, 2)
    except:
        return 0


@app.get("/")
def root():
    return {"message": "Cosmic Watch Backend Running"}


@app.get("/neo/feed")
def get_neo_feed():
    res = requests.get(NASA_URL)
    data = res.json()

    result = []

    for date in data["near_earth_objects"]:
        for neo in data["near_earth_objects"][date]:
            try:
                velocity = neo["close_approach_data"][0]["relative_velocity"]["kilometers_per_hour"]
                distance = neo["close_approach_data"][0]["miss_distance"]["kilometers"]
            except:
                velocity = "N/A"
                distance = "N/A"

            result.append({
                "id": neo["id"],
                "name": neo["name"],
                "hazardous": neo["is_potentially_hazardous_asteroid"],
                "velocity_kph": velocity,
                "miss_distance_km": distance,
                "risk_score": risk_score(neo)
            })

    return result
