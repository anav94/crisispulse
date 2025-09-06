import h3
def h3_from_latlon(lat, lon, res=7):
    if lat is None or lon is None: return None
    try: return h3.geo_to_h3(lat, lon, res)
    except Exception: return None
