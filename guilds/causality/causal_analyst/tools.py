from typing import Any, Dict, List

def run_causal_discovery(insights_data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Simulates a causal discovery process on a list of news insights.

    In a real system, this would involve complex statistical algorithms.
    Here, we mock the process by creating simple causal links based on sentiment.

    Args:
        insights_data: A list of insight dictionaries from the Insight-Miner.

    Returns:
        A dictionary representing a simplified causal graph.
    """
    print(f"TOOL EXECUTING: run_causal_discovery()")
    causal_links = []
    
    for insight in insights_data:
        headline = insight.get("headline", "Unknown Headline")
        sentiment = insight.get("sentiment", "Neutral")
        
        if "outlook" in headline.lower() and sentiment == "Positive":
            link = {
                "cause": f"Positive Sentiment in '{headline}'",
                "effect": "Increased Positive Price Expectation",
                "confidence": 0.75,
                "explanation": "Positive forward-looking statements often lead to bullish sentiment."
            }
            causal_links.append(link)
        elif "volatility" in headline.lower() and sentiment == "Negative":
            link = {
                "cause": f"Negative Sentiment in '{headline}'",
                "effect": "Increased Market Uncertainty",
                "confidence": 0.80,
                "explanation": "Reports on volatility directly contribute to market uncertainty."
            }
            causal_links.append(link)

    return {"status": "success", "causal_graph": {"links": causal_links}}