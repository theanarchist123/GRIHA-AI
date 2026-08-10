import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie
from database.models.activity_log import ActivityLog

async def main():
    client = AsyncIOMotorClient('mongodb+srv://kadamnikhil434:110kadam@cluster0.p1bns.mongodb.net/griha_ai?retryWrites=true&w=majority&appName=Cluster0')
    await init_beanie(database=client.griha_ai, document_models=[ActivityLog])
    
    query_filters = [{'$or': [{'user_id': 'user_2xdiV6uEHbWHv77T4ualt40KDpi'}, {'user_id': None}]}]
    raw_query = {'$and': query_filters}
    
    try:
        total = await ActivityLog.find_many(raw_query).count()
        activities = await ActivityLog.find_many(raw_query).sort('-created_at').to_list()
        
        print('Total:', total)
        print('Activities:', len(activities))
    except Exception as e:
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
