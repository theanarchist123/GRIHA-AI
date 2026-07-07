import asyncio
import httpx

async def test_autocomplete():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/126.0.0.0 Safari/537.36"
    }
    
    print("Testing NoBroker Autocomplete:")
    try:
        async with httpx.AsyncClient(verify=False) as client:
            res = await client.get("https://www.nobroker.in/api/v1/locality/autocomplete?input=Bandra%20West&city=mumbai", headers=headers)
            print(res.status_code, res.text[:200])
    except Exception as e:
        print(e)

    print("\nTesting Housing Autocomplete:")
    try:
        async with httpx.AsyncClient(verify=False) as client:
            res = await client.get("https://housing.com/api/v0/search/suggest?string=Bandra%20West", headers=headers)
            print(res.status_code, res.text[:200])
    except Exception as e:
        print(e)
        
    print("\nTesting 99acres Autocomplete:")
    try:
        async with httpx.AsyncClient(verify=False) as client:
            res = await client.get("https://www.99acres.com/api-aggregator/discovery/srp/search?keyword=Bandra%20West", headers=headers)
            print(res.status_code, res.text[:200])
    except Exception as e:
        print(e)

if __name__ == "__main__":
    asyncio.run(test_autocomplete())
