import requests

def parse_json_response(response: requests.Response) -> dict:
    """Parse JSON response while handling escape sequences."""
    text = response.text.replace(r"\/", "/")
    return response.json() 