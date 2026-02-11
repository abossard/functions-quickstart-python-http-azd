import azure.functions as func
import httpx
import requests

from log_setup import setup_logging

logger = setup_logging("function_app")

app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)

@app.route(route="httpget", methods=["GET"])
def http_get(req: func.HttpRequest) -> func.HttpResponse:
    name = req.params.get("name", "World")

    logger.info(f"Processing GET request. Name: {name}")

    # --- demo HTTP calls with both httpx and requests ---------------------
    url = "https://httpbin.org/get"

    # httpx
    logger.info("--- httpx ---")
    try:
        with httpx.Client(timeout=5) as client:
            resp = client.get(url)
            logger.info("httpx  %s → %s", url, resp.status_code)
    except httpx.HTTPError as exc:
        logger.warning("httpx  request failed: %s", exc)

    # requests
    logger.info("--- requests ---")
    try:
        resp = requests.get(url, timeout=5)
        logger.info("requests %s → %s", url, resp.status_code)
    except requests.RequestException as exc:
        logger.warning("requests request failed: %s", exc)

    return func.HttpResponse(f"Hello, {name}!")

@app.route(route="httppost", methods=["POST"])
def http_post(req: func.HttpRequest) -> func.HttpResponse:
    try:
        req_body = req.get_json()
        name = req_body.get('name')
        age = req_body.get('age')
        
        logger.info(f"Processing POST request. Name: {name}")

        if name and isinstance(name, str) and age and isinstance(age, int):
            return func.HttpResponse(f"Hello, {name}! You are {age} years old!")
        else:
            return func.HttpResponse(
                "Please provide both 'name' and 'age' in the request body.",
                status_code=400
            )
    except ValueError:
        return func.HttpResponse(
            "Invalid JSON in request body",
            status_code=400
        )
