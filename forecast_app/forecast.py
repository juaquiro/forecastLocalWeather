# Pure algorithm: session -> "BETTER" | "STABLE" | "WORSE" (or "NEED MORE DATA")

def classify(delta, thr=2.0):
    if delta > thr:
        return "BETTER"
    elif delta < -thr:
        return "WORSE"
    return "STABLE"

def forecast(session):
    """
    session: list of dicts like
        {"t": datetime, "alt": float, "temp": float, "dew": float, "rh": float}
    """
    if len(session) < 2:
        return "NEED MORE DATA"
    s0 = session[0]["temp"] - session[0]["dew"]
    sN = session[-1]["temp"] - session[-1]["dew"]
    return classify(sN - s0)
