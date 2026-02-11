import azure.functions as func
import httpx

from log_setup import setup_logging

logger = setup_logging("function_app")

app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)

@app.route(route="httpget", methods=["GET"])
def http_get(req: func.HttpRequest) -> func.HttpResponse:
    name = req.params.get("name", "World")

    logger.info(f"Processing GET request. Name: {name}")

    # --- demo HTTP calls to show logging in action ------------------------
    urls = [
        "https://httpbin.org/get",
        "https://httpbin.org/status/404",
        "https://httpbin.org/delay/1",
    ]
    with httpx.Client(timeout=5) as client:
        for url in urls:
            try:
                logger.debug("Requesting %s", url)
                resp = client.get(url)
                logger.info("%s → %s", url, resp.status_code)
            except httpx.HTTPError as exc:
                logger.warning("Request to %s failed: %s", url, exc)

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
