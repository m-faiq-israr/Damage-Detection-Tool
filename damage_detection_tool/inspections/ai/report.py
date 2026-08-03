import json


def generate_report(results):

    return json.dumps(
        results,
        indent=4,
        default=str
    )