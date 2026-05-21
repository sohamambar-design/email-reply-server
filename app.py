import logging
import os
import time
import uuid
import sys

from dotenv import load_dotenv
from flask import Flask, jsonify, request, g
from flask_cors import CORS

from routes.email_routes import email_bp


# ==========================================
# Load Environment Variables
# ==========================================

load_dotenv()


# ==========================================
# Logging Configuration
# ==========================================

def configure_logging() -> None:
    """
    Configure application-wide logging.
    """

    log_level = os.getenv("LOG_LEVEL", "INFO").upper()

    logging.basicConfig(
        level=log_level,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        force=True,
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler("app.log")
        ]
    )

    logging.getLogger("werkzeug").setLevel(log_level)


logger = logging.getLogger(__name__)


# ==========================================
# Flask Application Factory
# ==========================================

def create_app() -> Flask:
    """
    Create and configure Flask application.
    """

    configure_logging()

    app = Flask(__name__)

    # ==========================================
    # App Config
    # ==========================================

    app.config["MAX_CONTENT_LENGTH"] = 2 * 1024 * 1024  # 2 MB request limit

    CORS(app)

    # ==========================================
    # Register Blueprints
    # ==========================================

    app.register_blueprint(email_bp)

    # ==========================================
    # Request Middleware
    # ==========================================

    @app.before_request
    def before_request():
        """
        Runs before every request.
        """

        g.request_id = str(uuid.uuid4())

        request.start_time = time.time()

        request_preview = None
        if request.is_json:
            request_preview = request.get_json(silent=True)
        elif request.data:
            request_preview = request.data.decode("utf-8", errors="replace")

        logger.info(
            f"Incoming Request | "
            f"RequestID={g.request_id} | "
            f"Method={request.method} | "
            f"Path={request.path} | "
            f"Remote={request.remote_addr} | "
            f"Query={request.query_string.decode('utf-8', errors='replace')} | "
            f"Payload={request_preview}"
        )

    # ==========================================
    # Response Middleware
    # ==========================================

    @app.after_request
    def after_request(response):
        """
        Runs after every request.
        """

        duration = round(
            time.time() - request.start_time,
            3
        ) if hasattr(request, "start_time") else 0

        logger.info(
            f"Outgoing Response | "
            f"RequestID={getattr(g, 'request_id', 'N/A')} | "
            f"Method={request.method} | "
            f"Path={request.path} | "
            f"Status={response.status_code} | "
            f"Duration={duration}s"
        )

        # ==========================================
        # Security Headers
        # ==========================================

        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Cache-Control"] = "no-store"

        return response

    # ==========================================
    # Error Handlers
    # ==========================================

    @app.errorhandler(404)
    def not_found(_error):

        return (
            jsonify(
                {
                    "success": False,
                    "request_id": getattr(g, "request_id", "N/A"),
                    "error": "Route not found"
                }
            ),
            404,
        )

    @app.errorhandler(405)
    def method_not_allowed(_error):

        return (
            jsonify(
                {
                    "success": False,
                    "request_id": getattr(g, "request_id", "N/A"),
                    "error": "Method not allowed"
                }
            ),
            405,
        )

    @app.errorhandler(413)
    def payload_too_large(_error):

        return (
            jsonify(
                {
                    "success": False,
                    "request_id": getattr(g, "request_id", "N/A"),
                    "error": "Payload too large"
                }
            ),
            413,
        )

    @app.errorhandler(500)
    def internal_server_error(error):

        logger.exception(
            f"Unhandled server error | "
            f"RequestID={getattr(g, 'request_id', 'N/A')} | "
            f"Error={error}"
        )

        return (
            jsonify(
                {
                    "success": False,
                    "request_id": getattr(g, "request_id", "N/A"),
                    "error": "Internal server error"
                }
            ),
            500,
        )

    # ==========================================
    # Root Route
    # ==========================================

    @app.route("/", methods=["GET"])
    def root():

        return jsonify(
            {
                "success": True,
                "service": "Smart Email Reply Agent",
                "status": "running",
                "version": "1.0.0"
            }
        )

    return app


# ==========================================
# Create Flask App
# ==========================================

app = create_app()


# ==========================================
# Run Application
# ==========================================

if __name__ == "__main__":

    port = int(os.getenv("PORT", "5000"))

    debug = (
        os.getenv("FLASK_ENV", "production")
        == "development"
    )

    logger.info(
        f"Starting Flask Server | "
        f"Port={port} | "
        f"Debug={debug}"
    )

    app.run(
        host="0.0.0.0",
        port=port,
        debug=debug
    )