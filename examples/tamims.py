def capital(country: str):
    """
    Returns the capital of a country
    """
    capitals = {
        "France": "Paris",
        "Germany": "Berlin",
        "Italy": "Rome",
        "Japan": "Tokyo",
    }
    return capitals.get(country, "Unknown")


def language(country: str):
    """
    Return the language of a country
    """
    
    languages = {
        "France": "French",
        "Germany": "German",
        "Italy": "Italian",
        "Japan": "Japanese",
    }
    return languages.get(country, "Unknown")
