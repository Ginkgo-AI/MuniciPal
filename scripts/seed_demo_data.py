#!/usr/bin/env python3
"""Seed realistic demo data into a running Munici-Pal backend.

Usage:
    # Start the backend first:
    uvicorn municipal.web.app:create_app --factory --port 8080

    # Seed demo data:
    python3 scripts/seed_demo_data.py

    # Seed against a different host:
    python3 scripts/seed_demo_data.py --base-url http://localhost:9000

    # Clear demo data (restart the server — in-memory stores reset):
    # Simply stop and restart the uvicorn process.

This script populates the backend with realistic demo data by calling the
public API endpoints. All data flows through normal validation and business
logic, so it's identical to what a real user would produce.

Data created:
    - 6 chat sessions with realistic message histories
    - 6 intake cases (permits, FOIA, 311) at various stages
    - 4 standalone 311 service tickets
    - Approval queue entries (pending, approved, denied)
    - 3 payment records at different stages
    - Graph entities (parcels, owners, departments, contractors)
    - 5 notification records
    - 3 staff feedback entries
"""

from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime, timezone

import httpx

DEFAULT_BASE_URL = "http://localhost:8080"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def api(
    client: httpx.Client,
    method: str,
    path: str,
    *,
    json: dict | None = None,
    params: dict | None = None,
    staff_token: str | None = None,
) -> dict | list | None:
    """Make an API call and return parsed JSON, or exit on failure."""
    headers = {}
    if staff_token:
        headers["Authorization"] = f"Bearer {staff_token}"

    resp = client.request(method, path, json=json, params=params, headers=headers)
    if resp.status_code >= 400:
        print(f"  FAILED {method} {path} -> {resp.status_code}: {resp.text[:200]}")
        return None
    if resp.headers.get("content-type", "").startswith("application/json"):
        return resp.json()
    return None


def section(title: str) -> None:
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


# ---------------------------------------------------------------------------
# Staff login
# ---------------------------------------------------------------------------


def login_staff(client: httpx.Client) -> str | None:
    """Authenticate as staff and return the token."""
    section("Staff Authentication")
    username = os.environ.get("DEMO_STAFF_USER", "staff.admin")
    code = os.environ.get("DEMO_STAFF_CODE", "admin123")
    result = api(client, "POST", "/api/auth/login", json={
        "username": username,
        "code": code,
    })
    if result and result.get("success"):
        token = result["token"]
        print(f"  Logged in as {result.get('display_name', 'staff')} (tier: {result.get('tier')})")
        return token
    print("  WARNING: Staff login failed — staff endpoints will be unavailable")
    return None


# ---------------------------------------------------------------------------
# Chat sessions
# ---------------------------------------------------------------------------

DEMO_CONVERSATIONS = [
    {
        "session_type": "anonymous",
        "label": "Building Permit Inquiry",
        "messages": [
            ("How do I apply for a building permit?", None),
            ("What documents do I need for a residential addition?", None),
            ("How much does a building permit cost?", None),
            ("How long does the approval process take?", None),
        ],
    },
    {
        "session_type": "anonymous",
        "label": "Noise Ordinance Questions",
        "messages": [
            ("What are the noise ordinance hours in this city?", None),
            ("Can I file a complaint about my neighbor's construction noise?", None),
            ("What happens if someone violates the noise ordinance?", None),
        ],
    },
    {
        "session_type": "anonymous",
        "label": "FOIA Process Help",
        "messages": [
            ("How do I submit a FOIA request?", None),
            ("Is there a fee for public records?", None),
            ("How long does it take to get FOIA records back?", None),
        ],
    },
    {
        "session_type": "anonymous",
        "label": "311 Service Request",
        "messages": [
            ("There's a large pothole on Elm Street near the school.", None),
            ("Can I also report a broken streetlight on the same block?", None),
        ],
    },
    {
        "session_type": "verified",
        "label": "Permit Status Check",
        "messages": [
            ("I submitted a building permit last week. How do I check the status?", None),
            ("My permit number is BLD-2024-0042. Can you look it up?", None),
            ("When is the inspection scheduled?", None),
        ],
    },
    {
        "session_type": "authenticated",
        "label": "Fee Payment Question",
        "messages": [
            ("I need to pay the fee for my electrical permit.", None),
            ("What payment methods do you accept?", None),
        ],
    },
]


def seed_chat_sessions(client: httpx.Client) -> list[str]:
    """Create chat sessions with message history. Returns session IDs."""
    section("Chat Sessions")
    session_ids = []

    for conv in DEMO_CONVERSATIONS:
        # Create session
        result = api(client, "POST", "/api/sessions", json={
            "session_type": conv["session_type"],
        })
        if not result:
            continue
        sid = result["session_id"]
        session_ids.append(sid)
        print(f"  Session: {conv['label']} ({conv['session_type']}) -> {sid[:8]}...")

        # Send messages
        for user_msg, _ in conv["messages"]:
            api(client, "POST", "/api/chat", json={
                "session_id": sid,
                "message": user_msg,
            })
            print(f"    -> Sent: {user_msg[:50]}...")

    print(f"\n  Created {len(session_ids)} chat sessions")
    return session_ids


# ---------------------------------------------------------------------------
# Intake wizard cases
# ---------------------------------------------------------------------------

DEMO_CASES = [
    {
        "wizard_id": "permit_application",
        "label": "Building Permit — 742 Evergreen Terrace",
        "session_type": "authenticated",
        "steps": {
            "property_info": {
                "property_address": "742 Evergreen Terrace, Springfield, IL 62701",
                "parcel_id": "14-33-200-015",
                "property_type": "Residential",
            },
            "project_details": {
                "permit_type": "Building",
                "project_description": "Two-story residential addition including new master bedroom suite, bathroom, and expanded kitchen. Approximately 800 sqft total.",
                "estimated_cost": 125000,
                "start_date": "2026-04-15",
            },
            "documents": {},
            "review": {
                "applicant_name": "Homer Simpson",
                "applicant_email": "homer.simpson@springfield.net",
                "applicant_phone": "555-636-7890",
                "certify": True,
            },
        },
    },
    {
        "wizard_id": "permit_application",
        "label": "Electrical Permit — 316 Oak Avenue",
        "session_type": "authenticated",
        "steps": {
            "property_info": {
                "property_address": "316 Oak Avenue, Springfield, IL 62702",
                "parcel_id": "14-33-201-008",
                "property_type": "Residential",
            },
            "project_details": {
                "permit_type": "Electrical",
                "project_description": "Complete electrical panel upgrade from 100A to 200A service. Includes new subpanel for garage workshop.",
                "estimated_cost": 8500,
                "start_date": "2026-03-20",
            },
            "documents": {},
            "review": {
                "applicant_name": "Marge Simpson",
                "applicant_email": "marge@springfield.net",
                "applicant_phone": "555-636-7891",
                "certify": True,
            },
        },
    },
    {
        "wizard_id": "foia_request",
        "label": "FOIA — City Council Meeting Minutes",
        "session_type": "authenticated",
        "steps": {},
    },
    {
        "wizard_id": "service_request_311",
        "label": "311 — Large Pothole on Main Street",
        "session_type": "anonymous",
        "steps": {},
    },
    {
        "wizard_id": "permit_application",
        "label": "Plumbing Permit — 1024 Binary Lane",
        "session_type": "authenticated",
        "steps": {
            "property_info": {
                "property_address": "1024 Binary Lane, Springfield, IL 62703",
                "parcel_id": "14-33-205-003",
                "property_type": "Commercial",
            },
            "project_details": {
                "permit_type": "Plumbing",
                "project_description": "Restaurant kitchen plumbing renovation with grease trap installation and new commercial dishwasher connections.",
                "estimated_cost": 35000,
                "start_date": "2026-05-01",
            },
            "contractor_info": {
                "contractor_name": "Springfield Plumbing Co.",
                "contractor_license": "PL-2024-5567",
                "contractor_phone": "555-555-0199",
                "contractor_email": "info@springfieldplumbing.com",
            },
            "documents": {},
            "review": {
                "applicant_name": "Apu Nahasapeemapetilon",
                "applicant_email": "apu@kwik-e-mart.com",
                "applicant_phone": "555-555-0123",
                "certify": True,
            },
        },
    },
    {
        "wizard_id": "foia_request",
        "label": "FOIA — Police Department Budget",
        "session_type": "authenticated",
        "steps": {},
    },
]


def seed_intake_cases(client: httpx.Client, session_ids: list[str]) -> list[dict]:
    """Create intake wizard cases at various stages. Returns case info."""
    section("Intake Cases")
    cases = []

    for i, case_def in enumerate(DEMO_CASES):
        wizard_id = case_def["wizard_id"]

        # Start the wizard
        result = api(client, "POST", f"/api/intake/wizards/{wizard_id}/start")
        if not result:
            print(f"  SKIP: Could not start wizard {wizard_id}")
            continue

        state_id = result["state_id"]
        print(f"  Wizard: {case_def['label']} -> state {state_id[:8]}...")

        # Submit steps if we have step data
        if case_def["steps"]:
            # Get state to see available steps
            state = api(client, "GET", f"/api/intake/state/{state_id}")
            if state and state.get("steps"):
                for step in state["steps"]:
                    step_id = step["step_id"]
                    step_data = case_def["steps"].get(step_id, {})
                    if step_data or step_id in case_def["steps"]:
                        result = api(
                            client,
                            "POST",
                            f"/api/intake/state/{state_id}/steps/{step_id}",
                            json={
                                "data": step_data,
                                "session_type": case_def["session_type"],
                            },
                        )
                        if result:
                            print(f"    -> Step '{step_id}' submitted")

            # Try to submit the wizard as a complete case
            submit_result = api(client, "POST", f"/api/intake/state/{state_id}/submit")
            if submit_result and submit_result.get("id"):
                case_info = {
                    "case_id": submit_result["id"],
                    "wizard_id": wizard_id,
                    "label": case_def["label"],
                    "approval_request_id": submit_result.get("approval_request_id"),
                }
                cases.append(case_info)
                print(f"    -> Case submitted: {case_info['case_id'][:8]}...")
                if case_info["approval_request_id"]:
                    print(f"       Approval request: {case_info['approval_request_id'][:8]}...")
            else:
                print(f"    -> Could not submit (may need more steps)")
        else:
            print(f"    -> Wizard started (no steps submitted — placeholder)")

    print(f"\n  Created {len(cases)} submitted cases")
    return cases


# ---------------------------------------------------------------------------
# 311 Service Tickets
# ---------------------------------------------------------------------------

DEMO_TICKETS = [
    {
        "category": "road_maintenance",
        "description": "Large pothole approximately 2 feet wide and 6 inches deep on Elm Street between Oak and Pine, near the elementary school crosswalk. Multiple cars have been damaged.",
        "location": "Elm Street between Oak Ave and Pine Ave",
        "contact_name": "Ned Flanders",
        "contact_email": "ned.flanders@springfield.net",
        "contact_phone": "555-636-1234",
    },
    {
        "category": "streetlight",
        "description": "Streetlight at the corner of Maple Drive and 3rd Street has been flickering for two weeks and is now completely out. The intersection is very dark at night.",
        "location": "Corner of Maple Drive and 3rd Street",
        "contact_name": "Edna Krabappel",
        "contact_email": "edna.k@springfield.edu",
        "contact_phone": "555-636-5678",
    },
    {
        "category": "noise_complaint",
        "description": "Ongoing construction noise from commercial development site at 500 Industrial Parkway continuing well past 10 PM on weeknights. Affecting entire neighborhood.",
        "location": "500 Industrial Parkway",
        "contact_name": "Moe Szyslak",
        "contact_email": "moe@moetavern.com",
        "contact_phone": "555-636-9012",
    },
    {
        "category": "graffiti",
        "description": "Extensive graffiti on the retaining wall along Springfield Creek bike path, from the bridge to the park entrance. Approximately 200 feet of wall affected.",
        "location": "Springfield Creek Bike Path, south retaining wall",
        "contact_name": "Maude Flanders",
        "contact_email": "maude@springfield.net",
        "contact_phone": "555-636-3456",
    },
]


def seed_311_tickets(client: httpx.Client, session_ids: list[str]) -> list[str]:
    """Create 311 service tickets. Returns ticket IDs."""
    section("311 Service Tickets")
    ticket_ids = []

    for i, ticket in enumerate(DEMO_TICKETS):
        payload = {**ticket, "session_id": session_ids[i % len(session_ids)] if session_ids else "demo"}
        result = api(client, "POST", "/api/bridge/311/tickets", json=payload)
        if result:
            tid = result.get("ticket_id") or result.get("id", "unknown")
            ticket_ids.append(tid)
            print(f"  Ticket: {ticket['category']} at {ticket['location'][:40]}... -> {str(tid)[:8]}...")

            # Add a follow-up note to the first two tickets
            if i < 2:
                api(client, "POST", f"/api/bridge/311/tickets/{tid}/notes", json={
                    "author": "Staff Admin",
                    "content": f"Reviewed and prioritized. Crew dispatched for assessment on {datetime.now(timezone.utc).strftime('%Y-%m-%d')}.",
                    "session_id": "staff-demo",
                })
                print(f"    -> Added staff follow-up note")

    print(f"\n  Created {len(ticket_ids)} service tickets")
    return ticket_ids


# ---------------------------------------------------------------------------
# Approval actions (approve/deny some cases)
# ---------------------------------------------------------------------------


def seed_approval_actions(
    client: httpx.Client, cases: list[dict], staff_token: str | None,
) -> None:
    """Approve and deny some pending approval requests."""
    section("Approval Actions")

    if not staff_token:
        print("  SKIP: No staff token available")
        return

    # List pending approvals
    result = api(client, "GET", "/api/staff/approvals", staff_token=staff_token)
    if not result:
        print("  No pending approvals found")
        return

    pending = [r for r in result if r.get("status") == "pending"]
    print(f"  Found {len(pending)} pending approvals")

    for i, req in enumerate(pending):
        req_id = req["request_id"]
        if i == 0:
            # Approve the first one
            api(client, "POST", f"/api/staff/approvals/{req_id}/approve", json={
                "approver": "Jane Smith",
                "reason": "Application complete and compliant with zoning requirements.",
            }, staff_token=staff_token)
            # Some gates need 2 approvals
            api(client, "POST", f"/api/staff/approvals/{req_id}/approve", json={
                "approver": "Bob Johnson",
                "reason": "Supervisor approval — confirmed.",
            }, staff_token=staff_token)
            print(f"  Approved: {req.get('gate_type', 'unknown')} ({req_id[:8]}...)")
        elif i == 1:
            # Deny the second one
            api(client, "POST", f"/api/staff/approvals/{req_id}/deny", json={
                "approver": "Jane Smith",
                "reason": "Incomplete contractor licensing documentation. Please resubmit with valid license.",
            }, staff_token=staff_token)
            print(f"  Denied: {req.get('gate_type', 'unknown')} ({req_id[:8]}...)")
        else:
            # Leave remaining as pending
            print(f"  Pending: {req.get('gate_type', 'unknown')} ({req_id[:8]}...)")


# ---------------------------------------------------------------------------
# Payments
# ---------------------------------------------------------------------------


def seed_payments(client: httpx.Client, cases: list[dict]) -> None:
    """Create payment records for submitted cases."""
    section("Payments")

    if not cases:
        print("  SKIP: No cases to attach payments to")
        return

    payments = [
        {"case_index": 0, "amount": 280.00, "label": "Building permit fee"},
        {"case_index": 1, "amount": 150.00, "label": "Electrical permit fee"},
    ]

    for pmt in payments:
        idx = pmt["case_index"]
        if idx >= len(cases):
            continue
        case_id = cases[idx]["case_id"]
        result = api(client, "POST", f"/api/finance/payment/{case_id}", json={
            "amount": pmt["amount"],
            "requestor": "resident",
        })
        if result:
            pid = result.get("payment_id", "unknown")
            print(f"  Payment: {pmt['label']} (${pmt['amount']}) -> {str(pid)[:8]}...")
        else:
            print(f"  SKIP: Could not create payment for {pmt['label']}")


# ---------------------------------------------------------------------------
# Fee estimates
# ---------------------------------------------------------------------------


def seed_fee_estimates(client: httpx.Client) -> None:
    """Request fee estimates to demonstrate the finance engine."""
    section("Fee Estimates")

    estimates = [
        {
            "wizard_type": "permit",
            "data": {"permit_type": "Building", "square_footage": 800},
            "label": "Building permit (800 sqft addition)",
        },
        {
            "wizard_type": "permit",
            "data": {"permit_type": "Electrical"},
            "label": "Electrical permit",
        },
        {
            "wizard_type": "permit",
            "data": {"permit_type": "Demolition", "square_footage": 2000},
            "label": "Demolition permit (2000 sqft)",
        },
        {
            "wizard_type": "foia",
            "data": {"pages": 150},
            "label": "FOIA request (150 pages)",
        },
    ]

    for est in estimates:
        result = api(client, "POST", "/api/finance/estimate", json={
            "wizard_type": est["wizard_type"],
            "data": est["data"],
        })
        if result:
            total = result.get("total", "N/A")
            items = len(result.get("line_items", []))
            print(f"  {est['label']}: ${total} ({items} line items)")


# ---------------------------------------------------------------------------
# Notifications
# ---------------------------------------------------------------------------


def seed_notifications(client: httpx.Client, session_ids: list[str]) -> None:
    """Create notification records."""
    section("Notifications")

    if not session_ids:
        print("  SKIP: No sessions for notifications")
        return

    notifications = [
        {
            "recipient": "homer.simpson@springfield.net",
            "subject": "Permit Application Received — Case #BLD-2026-001",
            "body": "Your building permit application for 742 Evergreen Terrace has been received and is under review. Expected processing time: 10-15 business days.",
            "channel": "email",
            "priority": "normal",
            "template_id": "case_submitted",
        },
        {
            "recipient": "marge@springfield.net",
            "subject": "Permit Approved — Electrical Panel Upgrade",
            "body": "Your electrical permit application for 316 Oak Avenue has been approved. You may proceed with the work. Permit valid for 180 days.",
            "channel": "email",
            "priority": "normal",
            "template_id": "case_approved",
        },
        {
            "recipient": "apu@kwik-e-mart.com",
            "subject": "Permit Application Denied — Action Required",
            "body": "Your plumbing permit application for 1024 Binary Lane has been denied. Reason: Incomplete contractor licensing documentation. You may resubmit with the required documents.",
            "channel": "email",
            "priority": "high",
            "template_id": "case_denied",
        },
        {
            "recipient": "ned.flanders@springfield.net",
            "subject": "Service Request Update — Pothole Repair",
            "body": "Your 311 service request for the pothole on Elm Street has been received and assigned to the Public Works crew. Estimated repair date: within 5 business days.",
            "channel": "email",
            "priority": "normal",
            "template_id": "ticket_created",
        },
        {
            "recipient": "555-636-5678",
            "subject": "Streetlight Repair Scheduled",
            "body": "Repair crew scheduled for the streetlight at Maple Drive and 3rd Street. Expected completion: 2 business days.",
            "channel": "sms",
            "priority": "low",
        },
    ]

    for i, notif in enumerate(notifications):
        payload = {
            **notif,
            "session_id": session_ids[i % len(session_ids)],
        }
        result = api(client, "POST", "/api/notifications/send", json=payload)
        if result:
            nid = result.get("id", "unknown")
            print(f"  Notification: {notif['subject'][:50]}... -> {str(nid)[:8]}...")


# ---------------------------------------------------------------------------
# Staff feedback
# ---------------------------------------------------------------------------


def seed_staff_feedback(
    client: httpx.Client, session_ids: list[str], staff_token: str | None,
) -> None:
    """Create staff feedback entries."""
    section("Staff Feedback")

    if not staff_token or not session_ids:
        print("  SKIP: No staff token or sessions")
        return

    feedbacks = [
        {
            "session_index": 1,
            "message_index": 3,
            "flag_type": "inaccurate",
            "note": "The noise ordinance quiet hours are 10 PM to 7 AM, not 11 PM to 6 AM as stated. The 2025 ordinance update changed the times.",
            "staff_id": "jane.smith",
        },
        {
            "session_index": 2,
            "message_index": 1,
            "flag_type": "missing_info",
            "note": "Response should mention that commercial FOIA requests may have different fee schedules than residential. See updated policy memo from City Clerk.",
            "staff_id": "bob.johnson",
        },
        {
            "session_index": 0,
            "message_index": 5,
            "flag_type": "other",
            "note": "Good answer but could include a link to the online permit application portal for convenience.",
            "staff_id": "jane.smith",
        },
    ]

    for fb in feedbacks:
        idx = fb["session_index"]
        if idx >= len(session_ids):
            continue
        result = api(client, "POST", "/api/staff/feedback", json={
            "session_id": session_ids[idx],
            "message_index": fb["message_index"],
            "flag_type": fb["flag_type"],
            "note": fb["note"],
            "staff_id": fb["staff_id"],
        }, staff_token=staff_token)
        if result:
            fid = result.get("feedback_id", "unknown")
            print(f"  Feedback: {fb['flag_type']} on session {session_ids[idx][:8]}... -> {str(fid)[:8]}...")


# ---------------------------------------------------------------------------
# Shadow mode (enable on one session)
# ---------------------------------------------------------------------------


def seed_shadow_mode(
    client: httpx.Client, session_ids: list[str], staff_token: str | None,
) -> None:
    """Enable shadow mode on a session for demonstration."""
    section("Shadow Mode")

    if not staff_token or not session_ids:
        print("  SKIP: No staff token or sessions")
        return

    target = session_ids[0]
    result = api(client, "POST", "/api/staff/shadow", json={
        "session_id": target,
        "enabled": True,
    }, staff_token=staff_token)
    if result:
        print(f"  Shadow mode enabled on session {target[:8]}...")


# ---------------------------------------------------------------------------
# Verify seeded data
# ---------------------------------------------------------------------------


def verify_data(client: httpx.Client, staff_token: str | None) -> None:
    """Print a summary of seeded data by checking key endpoints."""
    section("Verification Summary")

    # Sessions
    sessions = api(client, "GET", "/api/sessions")
    print(f"  Chat sessions:    {len(sessions) if sessions else 0}")

    # Cases
    cases = api(client, "GET", "/api/intake/cases")
    print(f"  Intake cases:     {len(cases) if cases else 0}")

    # 311 tickets
    tickets = api(client, "GET", "/api/bridge/311/tickets")
    print(f"  311 tickets:      {len(tickets) if tickets else 0}")

    # Metrics (if staff token available)
    if staff_token:
        metrics = api(client, "GET", "/api/staff/metrics", staff_token=staff_token)
        if metrics:
            print(f"  Total sessions:   {metrics.get('total_sessions', 'N/A')}")
            print(f"  Active sessions:  {metrics.get('active_sessions', 'N/A')}")
            print(f"  Total cases:      {metrics.get('total_cases', 'N/A')}")
            print(f"  Pending approvals:{metrics.get('pending_approvals', 'N/A')}")
            print(f"  Approved:         {metrics.get('approved_count', 'N/A')}")
            print(f"  Denied:           {metrics.get('denied_count', 'N/A')}")

    # Fee schedules
    schedules = api(client, "GET", "/api/finance/schedule")
    if schedules:
        total_entries = sum(len(v) for v in schedules.values()) if isinstance(schedules, dict) else 0
        print(f"  Fee schedules:    {total_entries} entries")

    # Health
    health = api(client, "GET", "/api/health")
    if health:
        print(f"  Backend status:   {health.get('status', 'unknown')}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Seed demo data into a running Munici-Pal backend"
    )
    parser.add_argument(
        "--base-url",
        default=DEFAULT_BASE_URL,
        help=f"Backend base URL (default: {DEFAULT_BASE_URL})",
    )
    parser.add_argument(
        "--skip-chat",
        action="store_true",
        help="Skip chat sessions (faster seeding)",
    )
    args = parser.parse_args()

    print(f"Munici-Pal Demo Data Seeder")
    print(f"Target: {args.base_url}")
    print(f"Time:   {datetime.now(timezone.utc).isoformat()}")

    with httpx.Client(base_url=args.base_url, timeout=30.0) as client:
        # Check backend is running
        try:
            health = api(client, "GET", "/api/health")
            if not health:
                print("\nERROR: Backend is not responding. Start it first:")
                print("  uvicorn municipal.web.app:create_app --factory --port 8080")
                sys.exit(1)
        except httpx.ConnectError:
            print(f"\nERROR: Cannot connect to {args.base_url}")
            print("Start the backend first:")
            print("  uvicorn municipal.web.app:create_app --factory --port 8080")
            sys.exit(1)

        print(f"Backend: {health.get('status', 'unknown')} (v{health.get('version', '?')})")

        # Authenticate as staff
        staff_token = login_staff(client)

        # Seed data in order
        if args.skip_chat:
            session_ids = []
            # Create minimal sessions for other data to reference
            for st in ["anonymous", "verified", "authenticated"]:
                r = api(client, "POST", "/api/sessions", json={"session_type": st})
                if r:
                    session_ids.append(r["session_id"])
            print(f"\n  Created {len(session_ids)} minimal sessions (chat skipped)")
        else:
            session_ids = seed_chat_sessions(client)

        cases = seed_intake_cases(client, session_ids)
        seed_311_tickets(client, session_ids)
        seed_approval_actions(client, cases, staff_token)
        seed_payments(client, cases)
        seed_fee_estimates(client)
        seed_notifications(client, session_ids)
        seed_staff_feedback(client, session_ids, staff_token)
        seed_shadow_mode(client, session_ids, staff_token)
        verify_data(client, staff_token)

        section("Done")
        print("  Demo data seeded successfully!")
        print()
        print("  To clear all data, restart the backend server:")
        print("    # Stop uvicorn (Ctrl+C), then restart:")
        print("    uvicorn municipal.web.app:create_app --factory --port 8080")
        print()
        print("  Frontend URLs:")
        print("    Citizen portal:  http://localhost:3000")
        print("    Staff dashboard: http://localhost:3001")
        print(f"    Backend API:     {args.base_url}")
        print()


if __name__ == "__main__":
    main()
