import os
import replicate

REPLICATE_API_TOKEN = os.getenv("REPLICATE_API_TOKEN", "")


def get_replicate_client():
    return replicate.Client(api_token=REPLICATE_API_TOKEN)


def run_replicate(model_version: str, input_data: dict, timeout: int = 120):
    client = get_replicate_client()
    return client.run(model_version, input=input_data)
