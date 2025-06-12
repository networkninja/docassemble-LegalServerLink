# pre-load
from flask import request, jsonify
from flask_cors import cross_origin
from docassemble.base.util import get_config
from docassemble.webapp.app_object import app, csrf
from docassemble.webapp.server import api_verify, jsonify_with_status


@app.route("/lsinterviews", methods=["GET"])
@csrf.exempt
@cross_origin(origins="*", methods=["GET", "HEAD"], automatic_options=True)
def ls_interviews():
    """
    Endpoint to retrieve interview configurations for LegalServer.

    Returns:
        JSON response:
        - On success:
            {
                "interviews": [
                    {
                        "external": bool,
                        "sites": list,
                        "interview": str, # the path of the interview
                        "name": str,
                    }
                ]
            }
        - On error:
            {
                "error": str,
                "details": str (optional)
            }
    """
    try:
        if not api_verify(roles=["legalserver"]):
            return jsonify_with_status({"error": "Role verification failed."}, 403)
        legalserver_config = get_config("legalserver")
        if not legalserver_config:
            return jsonify_with_status(
                {"error": "Legalserver configuration not found."}, 404
            )
        interview_data = legalserver_config.get("interviews", [])
    except Exception as e:
        return jsonify_with_status(
            {
                "error": "An unexpected error occurred during role verification.",
                "details": str(e),
            },
            500,
        )

    if not isinstance(interview_data, list):
        return jsonify_with_status(
            {"error": "Invalid interview list data format."}, 400
        )
    else:
        for item in interview_data:
            item.setdefault("external", False)
            item.setdefault("sites", [])
            item.setdefault("name", "No Name")
            if item.get("interview") is None:
                interview_data.remove(item)

    return jsonify({"interviews": interview_data})
