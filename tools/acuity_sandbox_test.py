"""
Acuity sandbox live-test harness (stdlib only — no pip install needed).

Usage (on the call with ClearValue):
  1. Fill SANDBOX dict below, or set env vars ACUITY_BASE_URL / ACUITY_USERNAME
     / ACUITY_PASSWORD / ACUITY_SENDER_ID / ACUITY_RECIPIENT_ID /
     ACUITY_PRODUCT_CODE.
  2. python acuity_sandbox_test.py place-order
  3. Paste the response back into chat.

Extra modes:
  python acuity_sandbox_test.py dry-run     # print the XML, do NOT send
  python acuity_sandbox_test.py ping        # GET base URL, check auth/connectivity
"""
import argparse
import base64
import os
import ssl
import sys
import uuid
from datetime import datetime, timezone
from urllib import request as urlrequest
from urllib.error import HTTPError, URLError

SANDBOX = {
    "base_url": os.environ.get("ACUITY_BASE_URL", "TBD"),
    "username": os.environ.get("ACUITY_USERNAME", "TBD"),
    "password": os.environ.get("ACUITY_PASSWORD", "TBD"),
    "sender_id": os.environ.get("ACUITY_SENDER_ID", "TBD"),
    "recipient_id": os.environ.get("ACUITY_RECIPIENT_ID", "TBD"),
    "product_code": os.environ.get("ACUITY_PRODUCT_CODE", "TBD"),
}

SAMPLE_ORDER = {
    "partner_reference_number": f"OPTEON-TEST-{uuid.uuid4().hex[:8]}",
    "loan_number": "TEST-LOAN-001",
    "loan_type": "Conventional",
    "loan_purpose": "Purchase",
    "sales_price": "450000",
    "property_type": "SingleFamily",
    "address1": "123 Test St",
    "city": "Columbus",
    "state": "OH",
    "postal_code": "43215",
    "borrower_first": "Test",
    "borrower_last": "Borrower",
    "borrower_phone": "6145551234",
}


def build_acuity_order_xml(cfg: dict, order: dict) -> str:
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
    <PartnerReferenceNumber>{order['partner_reference_number']}</PartnerReferenceNumber>
    <ProductCode>{cfg['product_code']}</ProductCode>
  </OrderDetails>
  <Loan>
    <LoanNumber>{order['loan_number']}</LoanNumber>
    <LoanType>{order['loan_type']}</LoanType>
    <LoanPurpose>{order['loan_purpose']}</LoanPurpose>
  </Loan>
  <SubjectProperty>
    <Address1>{order['address1']}</Address1>
    <City>{order['city']}</City>
    <State>{order['state']}</State>
    <PostalCode>{order['postal_code']}</PostalCode>
    <PropertyType>{order['property_type']}</PropertyType>
    <SalesPrice>{order['sales_price']}</SalesPrice>
  </SubjectProperty>
  <Contacts>
    <Contact ContactType="Borrower">
      <FirstName>{order['borrower_first']}</FirstName>
      <LastName>{order['borrower_last']}</LastName>
      <DaytimePhone>{order['borrower_phone']}</DaytimePhone>
    </Contact>
  </Contacts>
</AcuityOrder>"""


def basic_auth_header(username: str, password: str) -> str:
    raw = f"{username}:{password}".encode("utf-8")
    return "Basic " + base64.b64encode(raw).decode("ascii")


def require_configured(cfg: dict) -> None:
    missing = [k for k, v in cfg.items() if v == "TBD"]
    if missing:
        print(f"ERROR: SANDBOX values still TBD: {missing}", file=sys.stderr)
        print("Fill SANDBOX dict at top of file, or set ACUITY_* env vars.", file=sys.stderr)
        sys.exit(2)


def do_request(method: str, url: str, body: bytes | None, headers: dict) -> None:
    req = urlrequest.Request(url, data=body, method=method, headers=headers)
    ctx = ssl.create_default_context()
    try:
        with urlrequest.urlopen(req, timeout=30, context=ctx) as resp:
            print(f"Status: {resp.status}")
            print("Headers:")
            for k, v in resp.headers.items():
                print(f"  {k}: {v}")
            print("\nBody:")
            print(resp.read().decode("utf-8", errors="replace"))
    except HTTPError as e:
        print(f"Status: {e.code} {e.reason}")
        print("Headers:")
        for k, v in e.headers.items():
            print(f"  {k}: {v}")
        print("\nBody:")
        print(e.read().decode("utf-8", errors="replace"))
    except URLError as e:
        print(f"URLError: {e.reason}", file=sys.stderr)
        sys.exit(1)


def place_order() -> None:
    require_configured(SANDBOX)
    xml = build_acuity_order_xml(SANDBOX, SAMPLE_ORDER)
    print("=== Request XML ===")
    print(xml)
    print(f"\n=== POST {SANDBOX['base_url']} ===\n")
    do_request(
        "POST",
        SANDBOX["base_url"],
        xml.encode("utf-8"),
        {
            "Content-Type": "application/xml",
            "Authorization": basic_auth_header(SANDBOX["username"], SANDBOX["password"]),
        },
    )
    print(f"\nPartnerReferenceNumber used: {SAMPLE_ORDER['partner_reference_number']}")


def dry_run() -> None:
    xml = build_acuity_order_xml(SANDBOX, SAMPLE_ORDER)
    print(xml)
    print(f"\nPartnerReferenceNumber: {SAMPLE_ORDER['partner_reference_number']}")


def ping() -> None:
    require_configured(SANDBOX)
    do_request(
        "GET",
        SANDBOX["base_url"],
        None,
        {"Authorization": basic_auth_header(SANDBOX["username"], SANDBOX["password"])},
    )


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("action", choices=["place-order", "dry-run", "ping"])
    args = ap.parse_args()
    {"place-order": place_order, "dry-run": dry_run, "ping": ping}[args.action]()
