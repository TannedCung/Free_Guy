"""
Author: Joon Sung Park (joonspk@stanford.edu)
File: views.py
"""

import json
import os

from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt


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
    data = json.loads(request.body)
    step = data["step"]
    sim_code = data["sim_code"]
    environment = data["environment"]

    from translator.models import EnvironmentState, Simulation

    try:
        sim = Simulation.objects.get(name=sim_code)
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
    data = json.loads(request.body)
    step = data["step"]
    sim_code = data["sim_code"]

    response_data: dict = {"<step>": -1}

    from translator.models import MovementRecord, Simulation

    try:
        sim = Simulation.objects.get(name=sim_code)
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
    data = json.loads(request.body)
    camera = data["camera"]

    from translator.models import RuntimeState

    RuntimeState.objects.update_or_create(
        key="path_tester_env",
        defaults={"value": camera},
    )

    return HttpResponse("received")
