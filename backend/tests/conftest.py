import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest

from app import create_app
from app.config import Config
from app.db import db as _db
from app.services.channels import reset_channel_clients
from app.services.ledger import reset_ledger_client
from app.services.whatsapp_bot import reset_sessions


class TestConfig(Config):
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    LEDGER_BACKEND = "stub"
    WHATSAPP_BACKEND = "dummy"
    SMS_BACKEND = "dummy"


@pytest.fixture()
def app(tmp_path):
    TestConfig.PHOTO_UPLOAD_DIR = tmp_path / "uploads"
    application = create_app(TestConfig)
    application.config["TESTING"] = True

    with application.app_context():
        yield application

    reset_ledger_client()
    reset_channel_clients()
    reset_sessions()


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def db(app):
    return _db


SAMPLE_PROJECTS = [
    {
        "id": "KASIKEU-2022-23-001",
        "ward": "Kasikeu",
        "county": "Makueni",
        "subward": "Cross-cutting",
        "sector": "Infrastructure",
        "project_name": "Manual opening and grading",
        "description": "Road opening near Kithina.",
        "financial_year": "2022/23",
        "allocated_amount_ksh": 1_000_000,
        "county_claimed_status": "delivered",
        "county_remarks": "5.6km opened and graded.",
        "source_document": "Kasikeu Ward Development Profile, 2025",
        "source_page": 11,
        "verification_status": "reported",
    },
    {
        "id": "KASIKEU-2024-25-041",
        "ward": "Kasikeu",
        "county": "Makueni",
        "subward": "Cross-cutting",
        "sector": "Agriculture",
        "project_name": "Rehabilitation of Kasikeu stock yard and toilet.",
        "description": "Rehabilitation of the stock yard and toilet.",
        "financial_year": "2024/25",
        "allocated_amount_ksh": 454_275,
        "county_claimed_status": "not_started",
        "county_remarks": "Fast track implementation",
        "source_document": "Kasikeu Ward Development Profile, 2025",
        "source_page": 15,
        "verification_status": "reported",
    },
]


@pytest.fixture()
def seeded_projects(app, db):
    from app.models import Project

    for record in SAMPLE_PROJECTS:
        db.session.add(Project(**record))
    db.session.commit()
    return SAMPLE_PROJECTS
