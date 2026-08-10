from fastapi import APIRouter
from database.models.property import Property

router = APIRouter(prefix="/api/market", tags=["Market Insights"])

@router.get("/heatmap")
async def get_market_heatmap():
    """
    Returns average rent and price per sqft grouped by locality.
    Useful for plotting heatmaps or bar charts of the market.
    """
    pipeline = [
        {
            "$match": {
                "is_fake": {"$ne": True},
                "price": {"$gt": 0}
            }
        },
        {
            "$group": {
                "_id": "$locality",
                "avg_rent": {"$avg": "$price"},
                "property_count": {"$sum": 1},
                "avg_sqft": {"$avg": "$size_sqft"}
            }
        },
        {
            "$match": {
                "property_count": {"$gte": 2} # Only include localities with at least 2 properties
            }
        },
        {
            "$sort": {"avg_rent": -1}
        },
        {
            "$limit": 20
        }
    ]
    
    results = await Property.aggregate(pipeline).to_list()
    
    # Format for frontend
    formatted_data = []
    for r in results:
        locality = r["_id"]
        if not locality:
            continue
            
        formatted_data.append({
            "locality": locality,
            "avg_rent": round(r["avg_rent"]),
            "property_count": r["property_count"],
            "avg_sqft": round(r["avg_sqft"]) if r["avg_sqft"] else None,
            "price_per_sqft": round(r["avg_rent"] / r["avg_sqft"]) if r["avg_sqft"] and r["avg_sqft"] > 0 else None
        })
        
    return {"status": "success", "data": formatted_data}
