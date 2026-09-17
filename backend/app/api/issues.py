from flask import Blueprint, current_app, jsonify, request

from ..models import IssueReport, ISSUE_CATEGORIES
from ..services.issue_service import (
    InvalidCategoryError,
    PhoneNotVerifiedError,
    RateLimitedError,
    submit_issue,
)
from ..services.uploads import save_photo

issues_bp = Blueprint("issues", __name__)


@issues_bp.get("/issues/categories")
def list_categories():
    return jsonify({"categories": ISSUE_CATEGORIES})


@issues_bp.get("/issues")
def list_issues():
    ward = request.args.get("ward")
    county = request.args.get("county")
    query = IssueReport.query.filter_by(active=True)
    if ward:
        query = query.filter(IssueReport.ward.ilike(ward))
    if county:
        query = query.filter(IssueReport.county.ilike(county))
    issues = query.order_by(IssueReport.submitted_at.desc()).all()
    return jsonify({"issues": [i.to_dict() for i in issues], "count": len(issues)})


@issues_bp.get("/issues/<issue_id>")
def get_issue(issue_id: str):
    issue = IssueReport.query.get(issue_id)
    if issue is None:
        return jsonify({"error": "not_found"}), 404
    return jsonify(issue.to_dict())


@issues_bp.post("/issues")
def create_issue():
    if request.content_type and "multipart/form-data" in request.content_type:
        form = request.form
        raw_phone = form.get("phone")
        county = form.get("county")
        ward = form.get("ward")
        category = form.get("category")
        title = form.get("title")
        description = form.get("description")
        gps_lat = form.get("gps_lat", type=float)
        gps_lon = form.get("gps_lon", type=float)
        photo_path = save_photo(request.files.get("photo"), current_app.config_class.PHOTO_UPLOAD_DIR)
    else:
        data = request.get_json(force=True) or {}
        raw_phone = data.get("phone")
        county = data.get("county")
        ward = data.get("ward")
        category = data.get("category")
        title = data.get("title")
        description = data.get("description")
        gps_lat = data.get("gps_lat")
        gps_lon = data.get("gps_lon")
        photo_path = None

    if not raw_phone or not county or not ward or not category or not title:
        return jsonify({
            "error": "phone, county, ward, category and title are required",
            "valid_categories": ISSUE_CATEGORIES,
        }), 400

    try:
        issue = submit_issue(
            raw_phone=raw_phone, county=county, ward=ward, category=category, title=title,
            description=description, photo_path=photo_path, gps_lat=gps_lat, gps_lon=gps_lon,
        )
    except InvalidCategoryError:
        return jsonify({"error": "invalid_category", "valid_categories": ISSUE_CATEGORIES}), 400
    except PhoneNotVerifiedError:
        return jsonify({"error": "phone_not_verified"}), 403
    except RateLimitedError:
        return jsonify({"error": "rate_limited"}), 429

    return jsonify({"issue": issue.to_dict()}), 201
