"""
Loads data/ward_projects.json (produced by app/services/pdf_ingest.py) into
the Project table. Idempotent: re-running upserts by id rather than
duplicating rows, so it's safe to run again after re-parsing the PDF.

    python seed.py
"""
import json

from app import create_app
from app.config import Config
from app.db import db
from app.models import Project


def seed() -> None:
    app = create_app()
    with app.app_context():
        with open(Config.SEED_DATA_PATH, "r", encoding="utf-8") as f:
            records = json.load(f)

        translations_path = Config.REPO_ROOT / "data" / "project_name_translations.json"
        name_translations: dict = {}
        if translations_path.exists():
            with open(translations_path, "r", encoding="utf-8") as f:
                name_translations = {k: v for k, v in json.load(f).items() if not k.startswith("_")}

        created, updated = 0, 0
        translated = 0
        for r in records:
            project = Project.query.get(r["id"])
            if project is None:
                project = Project(id=r["id"])
                db.session.add(project)
                created += 1
            else:
                updated += 1
            project.ward = r["ward"]
            project.county = r["county"]
            project.subward = r["subward"]
            project.sector = r["sector"]
            project.project_name = r["project_name"]
            project.description = r["description"]
            project.financial_year = r["financial_year"]
            project.allocated_amount_ksh = r["allocated_amount_ksh"]
            project.county_claimed_status = r["county_claimed_status"]
            project.county_remarks = r["county_remarks"]
            project.source_document = r["source_document"]
            project.source_page = r["source_page"]
            project.source_reference = r.get("source_reference", "")
            if not project.verification_status:
                project.verification_status = "reported"

            name_translation = name_translations.get(r["id"])
            if name_translation:
                project.project_name_sw = name_translation.get("sw")
                project.project_name_kam = name_translation.get("kam")
                translated += 1

        db.session.commit()
        print(f"Seeded {created} new projects, updated {updated} existing ones ({translated} with translated names).")


if __name__ == "__main__":
    seed()
