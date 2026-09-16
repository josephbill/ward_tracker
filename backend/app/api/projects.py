from flask import Blueprint, jsonify, request

from ..config import Config
from ..db import db
from ..models import Project
from ..services.translation import render_project_statement, supported_languages

projects_bp = Blueprint("projects", __name__)


def _lang_from_request() -> str:
    lang = request.args.get("lang", Config.DEFAULT_LANGUAGE)
    return lang if lang in Config.SUPPORTED_LANGUAGES else Config.DEFAULT_LANGUAGE


@projects_bp.get("/languages")
def list_languages():
    return jsonify({"supported": supported_languages(), "default": Config.DEFAULT_LANGUAGE})


@projects_bp.get("/counties")
def list_counties():
    """Every county with at least one ingested ward's data. This PoC only
    ships Makueni (Kasikeu ward) as the real, ingested sample — the endpoint
    itself is generic so any county's PDF can be dropped in via the same
    pdf_ingest.py pattern without an app-side code change."""
    rows = db.session.query(Project.county).distinct().order_by(Project.county).all()
    return jsonify({"counties": [r[0] for r in rows]})


@projects_bp.get("/wards")
def list_wards():
    """Wards with ingested project data, optionally scoped to one county
    (two different counties could otherwise share a ward name)."""
    county = request.args.get("county")
    query = db.session.query(Project.ward).distinct()
    if county:
        query = query.filter(Project.county.ilike(county))
    rows = query.order_by(Project.ward).all()
    return jsonify({"wards": [r[0] for r in rows]})


@projects_bp.get("/projects")
def list_projects():
    lang = _lang_from_request()
    ward = request.args.get("ward")
    county = request.args.get("county")
    query = Project.query
    if ward:
        query = query.filter(Project.ward.ilike(ward))
    if county:
        query = query.filter(Project.county.ilike(county))
    projects = query.order_by(Project.financial_year.desc(), Project.project_name).all()

    delivered_count = sum(1 for p in projects if p.county_claimed_status == "delivered")

    return jsonify(
        {
            "lang": lang,
            "count": len(projects),
            # "Purported" because this reflects the county's own claim, not
            # citizen verification — see verification_status per project for
            # what residents actually say.
            "purported_completion_rate": (delivered_count / len(projects)) if projects else 0,
            "delivered_count": delivered_count,
            "projects": [
                {**p.to_dict(), "project_name": p.display_name(lang), "statement": render_project_statement(p.to_dict(), lang)}
                for p in projects
            ],
        }
    )


@projects_bp.get("/projects/<project_id>")
def get_project(project_id: str):
    lang = _lang_from_request()
    project = Project.query.get(project_id)
    if project is None:
        return jsonify({"error": "not_found"}), 404

    active_reports = [r.to_dict() for r in project.reports if r.active]
    return jsonify(
        {
            **project.to_dict(),
            "project_name": project.display_name(lang),
            "statement": render_project_statement(project.to_dict(), lang),
            "reports": active_reports,
        }
    )
