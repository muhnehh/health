import json
import os
import re
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Optional
import math

app = FastAPI(title="Shifti - AI Clinic Finder")

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

class TriageRequest(BaseModel):
    symptoms: str
    language: str = "en"

class ClinicResponse(BaseModel):
    name: str
    address: str
    wait_time: str
    eta: str
    distance: str
    phone: str
    urgency_match: str
    whatsapp_message: str

class TriageResponse(BaseModel):
    clinics: List[ClinicResponse]
    urgency_level: str
    parsed_symptoms: str
    parsed_location: str

# Load clinic data
def load_clinics_data():
    with open("clinics_data.json", "r", encoding="utf-8") as f:
        return json.load(f)

def calculate_distance(lat1, lon1, lat2, lon2):
    """Calculate distance between two points using Haversine formula"""
    try:
        R = 6371  # Earth's radius in kilometers
        
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        
        a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        
        distance = R * c
        # Ensure minimum distance to prevent division by zero
        return max(0.5, distance)  # Minimum 0.5km
    except:
        return 1.0  # Default 1km if calculation fails

def analyze_symptoms_with_ai(symptoms: str, language: str):
    """Analyze symptoms using rule-based approach for reliable triage"""
    symptoms_lower = symptoms.lower()
    
    # Emergency keywords
    emergency_keywords = [
        'chest pain', 'heart attack', 'stroke', 'unconscious', 'bleeding heavily', 
        'severe bleeding', 'difficulty breathing', 'can\'t breathe', 'choking',
        'severe head injury', 'broken bone', 'fracture', 'seizure', 'overdose',
        'poisoning', 'severe burn', 'electric shock', 'allergic reaction severe',
        'anaphylaxis', 'severe abdominal pain'
    ]
    
    # High priority keywords
    high_keywords = [
        'severe pain', 'high fever', 'vomiting blood', 'blood in stool',
        'severe headache', 'migraine', 'severe diarrhea', 'dehydration',
        'kidney pain', 'severe back pain', 'infection', 'wound',
        'cut deep', 'burn', 'sprain'
    ]
    
    # Child-related keywords
    child_keywords = ['child', 'baby', 'infant', 'toddler', 'son', 'daughter', 'kid']
    
    # Fever keywords
    fever_keywords = ['fever', 'temperature', 'hot', 'burning up']
    
    # Location extraction
    locations = ['ajman', 'sharjah', 'dubai', 'al nahda', 'al bustan', 'corniche', 
                 'rumailah', 'nakheel', 'nuaimiya', 'karama']
    
    # Determine urgency
    urgency = "moderate"
    if any(keyword in symptoms_lower for keyword in emergency_keywords):
        urgency = "emergency"
    elif any(keyword in symptoms_lower for keyword in high_keywords):
        urgency = "high"
    elif any(keyword in symptoms_lower for keyword in fever_keywords):
        urgency = "moderate"
    else:
        urgency = "low"
    
    # Extract location
    location = None
    for loc in locations:
        if loc in symptoms_lower:
            location = loc.title()
            break
    
    # Determine age group
    age_group = None
    if any(keyword in symptoms_lower for keyword in child_keywords):
        age_group = "child"
    elif 'elderly' in symptoms_lower or 'senior' in symptoms_lower:
        age_group = "elderly"
    else:
        age_group = "adult"
    
    return {
        "symptoms": symptoms[:100],
        "urgency": urgency,
        "location": location,
        "age_group": age_group,
        "requires_immediate_care": urgency in ["emergency", "high"]
    }

def rank_clinics(clinics_data, analysis, user_location=None):
    """Rank clinics based on urgency, location, and availability"""
    ranked_clinics = []
    
    # Default Ajman center coordinates if no location provided
    default_lat, default_lon = 25.4052, 55.5136
    
    for clinic in clinics_data["clinics"]:
        # Calculate distance (using default location if not specified)
        distance = calculate_distance(
            default_lat, default_lon,
            clinic["coordinates"]["lat"], clinic["coordinates"]["lon"]
        )
        
        # Distance is already handled in calculate_distance function
        
        # Calculate ETA based on distance (rough estimate: 3-5 min per km in city)
        eta_minutes = max(5, int(distance * 4))
        
        # Adjust wait time based on urgency
        base_wait = clinic["typical_wait_minutes"]
        if analysis["urgency"] == "emergency":
            wait_time = "Emergency - Go Now"
            eta_display = f"{eta_minutes} min"
        elif analysis["urgency"] == "high":
            wait_time = f"{max(5, base_wait - 10)} min wait"
            eta_display = f"{eta_minutes} min"
        else:
            wait_time = f"{base_wait} min wait"
            eta_display = f"{eta_minutes} min"
        
        # Create WhatsApp message
        whatsapp_msg = f"Found clinic: {clinic['name']} - {clinic['address']}. ETA: {eta_minutes} min, Wait: {wait_time}. Shared via Shifti+"
        
        ranked_clinics.append({
            "name": clinic["name"],
            "address": clinic["address"],
            "wait_time": wait_time,
            "eta": eta_display,
            "distance": f"{distance:.1f} km",
            "phone": clinic["phone"],
            "urgency_match": analysis["urgency"].title(),
            "whatsapp_message": whatsapp_msg,
            "score": (1/distance) * (1/max(1, base_wait/10)) * (2 if analysis["urgency"] in ["high", "emergency"] else 1)
        })
    
    # Sort by score and return top 3
    ranked_clinics.sort(key=lambda x: x["score"], reverse=True)
    return ranked_clinics[:3]

@app.get("/")
async def root():
    return FileResponse("static/index.html")

@app.post("/triage", response_model=TriageResponse)
async def triage_symptoms(request: TriageRequest):
    try:
        # Load clinic data
        clinics_data = load_clinics_data()
        
        # Analyze symptoms with AI
        analysis = analyze_symptoms_with_ai(request.symptoms, request.language)
        
        # Rank and select best clinics
        ranked_clinics = rank_clinics(clinics_data, analysis)
        
        # Convert to ClinicResponse objects
        clinic_responses = []
        for clinic in ranked_clinics:
            clinic_responses.append(ClinicResponse(
                name=clinic["name"],
                address=clinic["address"],
                wait_time=clinic["wait_time"],
                eta=clinic["eta"],
                distance=clinic["distance"],
                phone=clinic["phone"],
                urgency_match=clinic["urgency_match"],
                whatsapp_message=clinic["whatsapp_message"]
            ))
        
        return TriageResponse(
            clinics=clinic_responses,
            urgency_level=analysis["urgency"],
            parsed_symptoms=analysis["symptoms"],
            parsed_location=analysis.get("location", "Ajman (default)")
        )
        
    except Exception as e:
        import traceback
        print(f"Error in triage endpoint: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Triage analysis failed: {str(e)}")

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "Shifti AI Clinic Finder"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
