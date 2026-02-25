import scraper

# Coming Saturday: 2026-02-28 -> '20260228'
date = '20260228'
facility_types = []  # No filter
parks = []  # No filter

try:
    results = scraper.fetch_reservations([date], facility_types, parks)
    print('Success! Number of results:', len(results))
    if results:
        print('First result:', results[0])
        print('Sample results:', results[:3])  # First 3
    else:
        print('No available reservations found.')
except Exception as e:
    print(f'Exception: {e}')
    import traceback
    traceback.print_exc()
