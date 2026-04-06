"""
Author: Joon Sung Park (joonspk@stanford.edu)
File: views.py
"""

import json
import os

from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt


def _parse_json_post(request):
    """Validate POST + JSON body and return (data, error_response)."""
    if request.method != "POST":
        return None, JsonResponse({"detail": "Method not allowed."}, status=405)

    if not request.body:
        return None, JsonResponse({"detail": "Request body must be valid JSON."}, status=400)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return None, JsonResponse({"detail": "Request body must be valid JSON."}, status=400)

    if not isinstance(data, dict):
        return None, JsonResponse({"detail": "JSON body must be an object."}, status=400)

    return data, None


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
    the EnvironmentState database table.

    ARGS:
      request: Django request
    RETURNS:
      HttpResponse: string confirmation message.
    """
    data, error_response = _parse_json_post(request)
    if error_response is not None:
        return error_response
    assert data is not None

    step = data.get("step")
    sim_code = data.get("sim_code")
    environment = data.get("environment")

    if step is None or sim_code is None or environment is None:
        return JsonResponse(
            {"detail": "step, sim_code, and environment are required."},
            status=400,
        )
    if not isinstance(step, int):
        return JsonResponse({"detail": "step must be an integer."}, status=400)
    if not isinstance(sim_code, str) or not sim_code.strip():
        return JsonResponse({"detail": "sim_code must be a non-empty string."}, status=400)
    if not isinstance(environment, dict):
        return JsonResponse({"detail": "environment must be an object."}, status=400)

    from translator.models import EnvironmentState, Simulation

    try:
        sim = Simulation.objects.get(name=sim_code.strip())
        EnvironmentState.objects.update_or_create(
            simulation=sim,
            step=step,
            defaults={"agent_positions": environment},
        )
    except Simulation.DoesNotExist:
        pass

    return HttpResponse("received")


@csrf_exempt  # Exempt: called from Phaser game loop via XMLHttpRequest (no HTML form/session context)
def update_environment(request):
    """
    <BACKEND to FRONTEND>
    This sends the backend computation of the persona behavior to the frontend
    visual server.
    It does this by reading the new movement information from
    the MovementRecord database table.

    ARGS:
      request: Django request
    RETURNS:
      HttpResponse
    """
    data, error_response = _parse_json_post(request)
    if error_response is not None:
        return error_response
    assert data is not None

    step = data.get("step")
    sim_code = data.get("sim_code")

    if step is None or sim_code is None:
        return JsonResponse({"detail": "step and sim_code are required."}, status=400)
    if not isinstance(step, int):
        return JsonResponse({"detail": "step must be an integer."}, status=400)
    if not isinstance(sim_code, str) or not sim_code.strip():
        return JsonResponse({"detail": "sim_code must be a non-empty string."}, status=400)

    response_data: dict = {"<step>": -1}

    from translator.models import MovementRecord, Simulation

    try:
        sim = Simulation.objects.get(name=sim_code.strip())
        record = MovementRecord.objects.filter(simulation=sim, step=step).first()
        if record is not None:
            response_data = dict(record.persona_movements)
            response_data["<step>"] = step
    except Simulation.DoesNotExist:
        pass

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
    data, error_response = _parse_json_post(request)
    if error_response is not None:
        return error_response
    assert data is not None

    if "camera" not in data:
        return JsonResponse({"detail": "camera is required."}, status=400)

    camera = data["camera"]

    from translator.models import RuntimeState

    RuntimeState.objects.update_or_create(
        key="path_tester_env",
        defaults={"value": camera},
    )

    return HttpResponse("received")
