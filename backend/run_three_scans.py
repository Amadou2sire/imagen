import asyncio
import json
import time

from main import _scrape_fake_products_task, state


async def run_once(run_index: int):
    start = time.time()
    await _scrape_fake_products_task()
    duration = time.time() - start
    return {
        "run": run_index,
        "count": state.get("fake_scrape_count", 0),
        "status": state.get("fake_scrape_status"),
        "errors_count": len(state.get("fake_scrape_errors", [])),
        "run_id": state.get("fake_scrape_run_id"),
        "duration_sec": round(duration, 2),
    }


async def main():
    results = []
    for i in range(1, 4):
        results.append(await run_once(i))

    counts = [r["count"] for r in results]
    stable = len(set(counts)) == 1

    payload = {
        "results": results,
        "counts": counts,
        "stable_same_count": stable,
    }
    print(json.dumps(payload, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(main())
