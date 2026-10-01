import os, json, re
from urllib.parse import quote_plus
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from app.models import User, get_db
from app.routes.auth import current_user
from app.routes.budget import build_summary

router = APIRouter(prefix="/api/ai", tags=["ai"])


class RecommendIn(BaseModel):
    category: str            # Home Decor, Event Planning, Jewelry Shopping ...
    budget: float = Field(gt=0)
    details: str = ""


PROMPT = """You are PocketSmart AI, a budget and shopping recommendation assistant for Indian shoppers.
Category: {category}
Total budget: INR {budget}
Extra details: {details}
User's budget status: {summary}

Return ONLY JSON (no markdown) in this shape:
{{"plan":[{{"item":"sub-item name","amount":number}}],
 "products":[{{"name":"short product name","search_query":"words to search on Amazon/Flipkart","price":approx INR number,"reason":"one line"}}],
 "tips":["saving tip"]}}
Rules: plan amounts add up to the budget (3-5 items). Give 5-6 products whose prices fit inside the plan. Prefer generic searchable products, not made-up brand models."""


def shop_links(query: str, price: float) -> dict:
    q = quote_plus(query)
    mx = int(price * 1.2)
    mn = int(price * 0.5)
    return {
        "amazon": f"https://www.amazon.in/s?k={q}&rh=p_36%3A{mn*100}-{mx*100}",
        "flipkart": f"https://www.flipkart.com/search?q={q}"
                    f"&p%5B%5D=facets.price_range.from%3D{mn}&p%5B%5D=facets.price_range.to%3D{mx}",
    }


def fallback(data: RecommendIn) -> dict:
    b = data.budget
    names = {"home": ["wall art", "led string lights", "cushion covers"],
             "event": ["party decoration kit", "balloon arch kit", "fairy lights"],
             "jewel": ["silver earrings", "gold plated necklace", "oxidised jewellery set"]}
    key = next((k for k in names if k in data.category.lower()), None)
    items = names.get(key, [data.category + " essentials", data.category + " combo", data.category + " kit"])
    return {"plan": [{"item": "Essentials", "amount": b * 0.5}, {"item": "Upgrades", "amount": b * 0.3},
                     {"item": "Reserve", "amount": b * 0.2}],
            "products": [{"name": n, "search_query": n, "price": b / 4, "reason": "Basic suggestion (Gemini key not set)"} for n in items],
            "tips": ["Compare Amazon and Flipkart prices before buying.", "Wait for sale days for big items."]}


@router.post("/recommend")
def recommend(data: RecommendIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    key = os.getenv("GEMINI_API_KEY")
    if not key:
        result = fallback(data)
    else:
        try:
            from google import genai
            from google.genai import types
            client = genai.Client(api_key=key)
            prompt = PROMPT.format(category=data.category, budget=data.budget,
                                   details=data.details or "none", summary=build_summary(db, user.id))
            res = client.models.generate_content(
                model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"), contents=prompt,
                config=types.GenerateContentConfig(response_mime_type="application/json"))
            result = json.loads(re.sub(r"^```json|```$", "", res.text.strip()).strip())
        except Exception as e:
            raise HTTPException(502, f"Gemini error: {e}")
    for p in result.get("products", []):
        p["links"] = shop_links(p.get("search_query") or p["name"], float(p.get("price") or data.budget / 4))
    return result
