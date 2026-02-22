"""
QC-Check 02 — Vision Language Model (VLM) Integration
Uses Google Gemini (or OpenAI) to analyze design spec images.
"""
import os
import json
import base64
import requests
import google.generativeai as genai
from config import GOOGLE_API_KEY

has_genai = False
if GOOGLE_API_KEY:
    try:
        genai.configure(api_key=GOOGLE_API_KEY)
        has_genai = True
    except Exception as e:
        print(f"Warning: Failed to configure Gemini: {e}")

def analyze_spec(image_path: str) -> dict:
    """
    Analyze a design spec image and return a list of components.
    
    Args:
        image_path: Path to the image file.
        
    Returns:
        {
            "components": [
                {"name": "M12 Connector", "count": 2, "details": "5-pin male"},
                ...
            ],
            "raw_text": "..."
        }
    """
    if not os.path.exists(image_path):
        return {"error": "Image file not found"}

    if has_genai:
        return _analyze_with_gemini(image_path)
    
    # Fallback / Mock if no API key
    return {
        "warning": "No API Key configured. Returning mock data.",
        "components": [
            {"name": "M12 Connector (Male)", "count": 2, "details": "5-pin, straight"},
            {"name": "PVC Cable Jacket", "count": 1, "details": "Black, 2m"},
            {"name": "Copper Wire", "count": 5, "details": "24AWG, stranded"},
            {"name": "Shielding", "count": 1, "details": "Braided copper"},
            {"name": "Strain Relief", "count": 2, "details": "Black rubber"}
        ],
        "raw_text": "Mock analysis result."
    }

def _analyze_with_gemini(image_path: str) -> dict:
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        # Read image
        with open(image_path, "rb") as f:
            image_data = f.read()
            
        prompt = """
        Analyze this technical drawing/schematic. 
        Focus on extracting the Bill of Materials (BOM) table if present.
        Identify all components listed.
        Return a JSON object with a key 'components'.
        Each component object MUST have:
        - 'part_number' (string, from 'Part Number' column if available, else null)
        - 'name' (string, from 'Description' column or label)
        - 'count' (number, from 'Qty' column. If "AR" or unspecified, estimate or use 1)
        - 'details' (string, extra info)
        
        Example: 
        { 
          "components": [ 
            {"part_number": "123-456", "name": "M12 Connector", "count": 2, "details": "Male 5-pin"},
            {"part_number": null, "name": "Cable", "count": 1, "details": "Shielded"}
          ] 
        }
        Output ONLY valid JSON.
        """
        
        response = model.generate_content([
            {'mime_type': 'image/jpeg', 'data': image_data},
            prompt
        ])
        
        text = response.text
        # Clean markdown code blocks if present
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0]
        elif "```" in text:
            text = text.split("```")[1].split("```")[0]
            
        try:
            data = json.loads(text)
            return data
        except json.JSONDecodeError:
            return {"error": "Failed to parse API response", "raw_text": text}
            
    except Exception as e:
        return {"error": str(e)}
