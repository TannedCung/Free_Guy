"""
Author: Joon Sung Park (joonspk@stanford.edu)
File: views.py
"""

import json
import os

from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from global_methods import check_if_file_exists


def spa_index(request):
    """Serve the React SPA index.html for all non-API, non-admin routes."""
    index_path = os.path.join(settings.REACT_DIST_DIR, "index.html")
    with open(index_path, "rb") as f:
        return HttpResponse(f.read(), content_type="text/html")


@csrf_exempt  # Exempt: called from Phaser game loop via XMLHttpRequest (no HTML form/session context)
def process_environment(request):
    """
    <FRONTEND to BACKEND>
    This sends the frontend visual world information to the backend server.
    It does this by writing the current environment representation to
    "storage/environment.json" file.

    ARGS:
      request: Django request
    RETURNS:
      HttpResponse: string confirmation message.
    """
    data = json.loads(request.body)
    step = data["step"]
    sim_code = data["sim_code"]
    environment = data["environment"]

    with open(f"storage/{sim_code}/environment/{step}.json", "w") as outfile:
        outfile.write(json.dumps(environment, indent=2))

    return HttpResponse("received")


@csrf_exempt  # Exempt: called from Phaser game loop via XMLHttpRequest (no HTML form/session context)
def update_environment(request):
    """
    <BACKEND to FRONTEND>
    This sends the backend computation of the persona behavior to the frontend
    visual server.
    It does this by reading the new movement information from
    "storage/movement.json" file.

    ARGS:
      request: Django request
    RETURNS:
      HttpResponse
    """
    data = json.loads(request.body)
    step = data["step"]
    sim_code = data["sim_code"]

    response_data = {"<step>": -1}
    if check_if_file_exists(f"storage/{sim_code}/movement/{step}.json"):
        with open(f"storage/{sim_code}/movement/{step}.json") as json_file:
            response_data = json.load(json_file)
            response_data["<step>"] = step

    return JsonResponse(response_data)


@csrf_exempt  # Exempt: called from path tester via XMLHttpRequest (internal tool, no form/session context)
def path_tester_update(request):
    """
    Processing the path and saving it to path_tester_env.json temp storage for
    conducting the path tester.

    ARGS:
      request: Django request
    RETURNS:
      HttpResponse: string confirmation message.
    """
    data = json.loads(request.body)
    camera = data["camera"]

    with open("temp_storage/path_tester_env.json", "w") as outfile:
        outfile.write(json.dumps(camera, indent=2))

    return HttpResponse("received")
