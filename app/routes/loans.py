from flask import Blueprint, jsonify

bp = Blueprint("loans", __name__)

@bp.route("/test", methods=["GET"])
def test_transaction():
    return jsonify({"message": "loans API is working!"})
