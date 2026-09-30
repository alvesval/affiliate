def calculate_score(price: float, original_price: float, commission_rate: float) -> dict:
    """Preliminary prioritization only; NOT predicted conversion or verified discount."""
    commission_value = round(max(0,price) * max(0,commission_rate) / 100,2)
    score = round(min(100, max(0,commission_rate)*5 + min(30,commission_value/3)),1)
    return {"score":score,"expected_commission":commission_value,"discount_pct":None}
