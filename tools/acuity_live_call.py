"""
Interactive live-call assistant for the ClearValue / Acuity sandbox meeting.

Walks you step-by-step through:
  1. Collecting the 6 sandbox values
  2. Confirming inbound endpoint plan
  3. Previewing the outgoing XML (dry-run)
  4. Firing a live place-order request
  5. Saving the response for the session log

Stdlib only. Run from C:\\Repos\\AcuityIntegration\\tools\\:
  py -3 acuity_live_call.py

Values are cached to `tools/.acuity_sandbox.local.json` between runs (gitignored).
"""
from __future__ import annotations

import base64
import json
import os
import ssl
import sys
import uuid
from datetime import datetime, timezone
from getpass import getpass
from pathlib import Path
from urllib import request as urlrequest
from urllib.error import HTTPError, URLError

HERE = Path(__file__).resolve().parent
CACHE = HERE / ".acuity_sandbox.local.json"
SAMPLES_DIR = HERE.parent / "samples"

FIELDS = [
    ("base_url", "Sandbox POST URL (e.g. https://clients.valorvaluations.com/<path>)", False),
    ("username", "Basic Auth username", False),
    ("password", "Basic Auth password", True),
    ("master_client_id", "Master Client ID (Valor sandbox: 56135)", False),
    ("branch_id", "Branch ID (Valor sandbox: 1055)", False),
    ("sender_id", "SenderID (Opteon's ID in Acuity)", False),
    ("recipient_id", "RecipientID (Valor's ID in Acuity)", False),
    ("product_code_pdr", "Product code — PDR (TBD from ClearValue; requires CaseFile or LPA)", False),
    ("product_code_pdc", "Product code — PDC (Valor = 9)", False),
    ("fast_complete_code", "Fast-complete sandbox product code (optional, press Enter to skip)", False),
    ("inbound_url", "Inbound URL we'll hand ClearValue (e.g. a webhook.site URL)", False),
]


def banner(text: str) -> None:
    print()
    print("=" * 72)
    print(f" {text}")
    print("=" * 72)


def load_cache() -> dict:
    if CACHE.exists():
        try:
            return json.loads(CACHE.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def save_cache(data: dict) -> None:
    CACHE.write_text(json.dumps(data, indent=2), encoding="utf-8")
    print(f"  (saved to {CACHE.name})")


def prompt(label: str, default: str | None, secret: bool) -> str:
    suffix = f" [{('*' * 8) if secret and default else (default or '')}]" if default else ""
    while True:
        raw = (getpass if secret else input)(f"  {label}{suffix}: ").strip()
        if raw:
            return raw
        if default is not None:
            return default
        if "optional" in label.lower():
            return ""
        print("    (required — please enter a value)")


def collect_values(cache: dict) -> dict:
    banner("STEP 1 — Collect sandbox values from ClearValue")
    print("Ask the ClearValue team for each of these. Press Enter to accept cached value.\n")
    out = dict(cache)
    for key, label, secret in FIELDS:
        out[key] = prompt(label, cache.get(key), secret)
    save_cache(out)
    return out


def confirm_security(cache: dict) -> dict:
    banner("STEP 2 — Security / delivery questions (capture answers)")
    questions = [
        ("ip_allowlist", "Does ClearValue require an IP allowlist? (y/n/unknown)"),
        ("tls_version", "Minimum TLS version required (default 1.2)"),
        ("mtls", "mTLS / cert pinning required? (y/n)"),
        ("rate_limit", "Rate limits (requests/minute, or 'none-stated')"),
        ("dup_ref_behavior", "Behavior on duplicate PartnerReferenceNumber (rejected/accepted)"),
        ("inbound_retry", "Do they retry inbound delivery on 5xx? (y/n)"),
    ]
    answers = dict(cache.get("answers", {}))
    for key, label in questions:
        default = answers.get(key)
        suffix = f" [{default}]" if default else ""
        raw = input(f"  {label}{suffix}: ").strip()
        answers[key] = raw or default or ""
    cache["answers"] = answers
    save_cache(cache)
    return cache


def build_xml(cfg: dict, product_code: str, partner_ref: str) -> str:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<AcuityOrder xmlns="http://www.acuityexchange.com/schemas/v6.4.0" SchemaVersion="6.4.0">
  <MessageHeader>
    <MessageID>{uuid.uuid4()}</MessageID>
    <SentDateTime>{now}</SentDateTime>
    <SenderID>{cfg['sender_id']}</SenderID>
    <RecipientID>{cfg['recipient_id']}</RecipientID>
  </MessageHeader>
  <OrderDetails>
    <PartnerReferenceNumber>{partner_ref}</PartnerReferenceNumber>
    <ProductCode>{product_code}</ProductCode>
    <MasterClientID>{cfg['master_client_id']}</MasterClientID>
    <BranchID>{cfg['branch_id']}</BranchID>
  </OrderDetails>
  <Loan>
    <LoanNumber>TEST-LOAN-001</LoanNumber>
    <LoanType>Conventional</LoanType>
    <LoanPurpose>Purchase</LoanPurpose>
  </Loan>
  <SubjectProperty>
    <Address1>123 Test St</Address1>
    <City>Columbus</City>
    <State>OH</State>
    <PostalCode>43215</PostalCode>
    <PropertyType>SingleFamily</PropertyType>
    <SalesPrice>450000</SalesPrice>
  </SubjectProperty>
  <Contacts>
    <Contact ContactType="Borrower">
      <FirstName>Test</FirstName>
      <LastName>Borrower</LastName>
      <DaytimePhone>6145551234</DaytimePhone>
    </Contact>
  </Contacts>
</AcuityOrder>"""


def basic_auth(username: str, password: str) -> str:
    raw = f"{username}:{password}".encode("utf-8")
    return "Basic " + base64.b64encode(raw).decode("ascii")


def choose_product_code(cfg: dict) -> str:
    print("\n  Which product code to send?")
    options = [("1", "PDR", cfg.get("product_code_pdr", "")),
               ("2", "PDC", cfg.get("product_code_pdc", ""))]
    if cfg.get("fast_complete_code"):
        options.append(("3", "Fast-complete", cfg["fast_complete_code"]))
    for num, name, val in options:
        print(f"    [{num}] {name:<15} ({val or 'not set'})")
    choice = input("  Choice (default 1): ").strip() or "1"
    for num, name, val in options:
        if num == choice:
            if not val:
                print(f"  (No value for {name} — falling back to PDR)")
                return cfg["product_code_pdr"]
            return val
    return cfg["product_code_pdr"]


def post_order(cfg: dict, xml: str) -> tuple[int, dict, str]:
    req = urlrequest.Request(
        cfg["base_url"],
        data=xml.encode("utf-8"),
        method="POST",
        headers={
            "Content-Type": "application/xml",
            "Authorization": basic_auth(cfg["username"], cfg["password"]),
        },
    )
    ctx = ssl.create_default_context()
    try:
        with urlrequest.urlopen(req, timeout=30, context=ctx) as resp:
            return resp.status, dict(resp.headers), resp.read().decode("utf-8", errors="replace")
    except HTTPError as e:
        return e.code, dict(e.headers), e.read().decode("utf-8", errors="replace")


def save_sample(name: str, content: str) -> Path:
    SAMPLES_DIR.mkdir(exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    path = SAMPLES_DIR / f"{ts}_{name}.xml"
    path.write_text(content, encoding="utf-8")
    return path


def run_test(cfg: dict) -> None:
    banner("STEP 3 — Preview the XML (dry-run)")
    partner_ref = f"OPTEON-TEST-{uuid.uuid4().hex[:8]}"
    product_code = choose_product_code(cfg)
    xml = build_xml(cfg, product_code, partner_ref)
    print(xml)
    print(f"\n  PartnerReferenceNumber: {partner_ref}")
    print(f"  ProductCode:            {product_code}")
    print(f"  POST target:            {cfg['base_url']}")

    banner("STEP 4 — Send it?")
    go = input("  Send this order to Acuity now? (y/N): ").strip().lower()
    if go != "y":
        print("  Skipped. Re-run script when ready.")
        return

    sent_path = save_sample(f"acuity_order_{partner_ref}", xml)
    print(f"  Saved outgoing XML → {sent_path}")

    print("\n  Sending...")
    status, headers, body = post_order(cfg, xml)
    print(f"\n  Status: {status}")
    print("  Headers:")
    for k, v in headers.items():
        print(f"    {k}: {v}")
    print("\n  Body:")
    print(body)

    resp_path = save_sample(f"acuity_ack_{partner_ref}", body)
    print(f"\n  Saved response → {resp_path}")

    banner("STEP 5 — Next")
    print(f"  1. Give ClearValue your inbound URL: {cfg['inbound_url']}")
    print(f"  2. Ask them to push an AcuityReport back for PartnerReferenceNumber={partner_ref}")
    print(f"  3. When it arrives, save the XML body to {SAMPLES_DIR}/<timestamp>_acuity_report.xml")
    print(f"  4. Paste the status + body into chat so we can wire the real values into env vars + flows.")


def main() -> None:
    banner("Acuity live-call assistant")
    print("This will walk you through the ClearValue sandbox test step by step.")
    print(f"Cached values file: {CACHE}")
    cache = load_cache()
    if cache:
        print(f"  Found cached values for: {sorted(k for k, v in cache.items() if v and k != 'answers')}")

    cfg = collect_values(cache)
    confirm_security(cfg)
    run_test(cfg)

    banner("Done")
    print("Re-run this script anytime — cached values will be pre-filled.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n(aborted)")
        sys.exit(130)
