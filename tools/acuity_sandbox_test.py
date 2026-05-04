"""
Acuity sandbox live-test harness (stdlib only — no pip install needed).

Updated 2026-05-04 to match the actual Acuity 6.4.0 XSD package
(downloaded from https://providers.clearvalueconsulting.com/artifacts/6.4.0.zip).
The April-vintage version of this script invented MessageHeader / OrderDetails /
Contacts wrappers that don't exist in the real schema, used the wrong default
XML namespace, used the wrong PropertyType enum value (SingleFamily instead of
SingleFamilyResidence — the same bug Valor caught with the 0500 error sample),
and was missing several required elements (System, MessageVersion,
ConditionalAcceptanceAllowed, RushOrder, EstimatedValue, PropertyOccupancy).

Reference: /tmp/acuity-xsd/6.4.0/ORDER.xml + XSD/AcuityOrder.xsd

Usage:
  1. Set env vars (don't bake creds into the file):
       ACUITY_USERNAME, ACUITY_PASSWORD, ACUITY_SENDER_ID
       (URL, RecipientID, ProductCode have working defaults)
  2. python acuity_sandbox_test.py dry-run    # print XML, do NOT send
  3. python acuity_sandbox_test.py place-order # send a real test POST
  4. python acuity_sandbox_test.py ping        # GET base URL, check auth/connectivity

The default sample order uses TestTransaction=true and a unique
PartnerReferenceNumber to avoid collisions with real orders.
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

# Endpoint + RecipientID + PDC code confirmed by Valor on 2026-05-04.
# PDR ProductCode still TBD as of that date.
SANDBOX = {
    "base_url": os.environ.get(
        "ACUITY_BASE_URL",
        "https://clients.valorvaluations.com/adapters/Integration/Acuity",
    ),
    "username": os.environ.get("ACUITY_USERNAME", "TBD"),
    "password": os.environ.get("ACUITY_PASSWORD", "TBD"),
    "sender_id": os.environ.get("ACUITY_SENDER_ID", "TBD"),
    "recipient_id": os.environ.get("ACUITY_RECIPIENT_ID", "VALOR"),
    "product_code": os.environ.get("ACUITY_PRODUCT_CODE", "9"),  # 9 = PDC
}

SAMPLE_ORDER = {
    "partner_reference_number": f"OPTEON-TEST-{uuid.uuid4().hex[:8]}",
    "loan_number": "TEST-LOAN-001",
    "loan_type": "Conventional",
    "loan_purpose": "Purchase",
    "sales_price": "450000",
    # PropertyType MUST be a value from AcuityPropertyType enum
    # (SingleFamilyResidence, Condominium, etc.). Generic strings like
    # "SingleFamily" trigger ErrorCode 0500.
    "property_type": "SingleFamilyResidence",
    "address1": "123 Test St",
    "city": "Columbus",
    "state": "OH",
    "postal_code": "43215",
    "borrower_first": "Test",
    "borrower_last": "Borrower",
    "borrower_phone": "6145551234",
    "borrower_email": "test.borrower@example.com",
}


def _xml_escape(s: str) -> str:
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )


def build_acuity_order_xml(cfg: dict, order: dict, test_transaction: bool = True) -> str:
    """Build an AcuityOrder XML matching schema 6.4.0 exactly.

    Required elements per AcuityOrder.xsd (minOccurs="1"):
      - ConditionalAcceptanceAllowed, BillingType, ServiceFee, TestTransaction,
        RushOrder, EstimatedValue, PropertyOccupancy
    Plus the message-envelope elements that ORDER.xml shows on every sample:
      - SenderID, RecipientID, MessageDate, System, MessageVersion,
        PartnerReferenceNumber, LineItemNumber, ProductCode
    """
    # ISO 8601 with offset, matching the sample format
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.0000000+00:00")
    parts = [
        '<?xml version="1.0" encoding="utf-8"?>',
        '<AcuityOrder xmlns:xsd="http://www.w3.org/2001/XMLSchema"'
        ' xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">',
        f"  <SenderID>{_xml_escape(cfg['sender_id'])}</SenderID>",
        f"  <RecipientID>{_xml_escape(cfg['recipient_id'])}</RecipientID>",
        f"  <MessageDate>{now}</MessageDate>",
        "  <System>Acuity</System>",
        "  <MessageVersion>6.4</MessageVersion>",
        f"  <PartnerReferenceNumber>{_xml_escape(order['partner_reference_number'])}</PartnerReferenceNumber>",
        "  <LineItemNumber>1</LineItemNumber>",
        f"  <ProductCode>{_xml_escape(cfg['product_code'])}</ProductCode>",
        "  <ConditionalAcceptanceAllowed>false</ConditionalAcceptanceAllowed>",
        "  <BillingType>Invoice</BillingType>",
        "  <Loan>",
        f"    <LoanType>{_xml_escape(order['loan_type'])}</LoanType>",
        f"    <LoanPurpose>{_xml_escape(order['loan_purpose'])}</LoanPurpose>",
        f"    <LoanNumber>{_xml_escape(order['loan_number'])}</LoanNumber>",
        "  </Loan>",
        "  <SubjectProperty>",
        f"    <Address1>{_xml_escape(order['address1'])}</Address1>",
        f"    <City>{_xml_escape(order['city'])}</City>",
        f"    <State>{_xml_escape(order['state'])}</State>",
        f"    <PostalCode>{_xml_escape(order['postal_code'])}</PostalCode>",
        f"    <SalesPrice>{_xml_escape(order['sales_price'])}</SalesPrice>",
        f"    <PropertyType>{_xml_escape(order['property_type'])}</PropertyType>",
        "  </SubjectProperty>",
        "  <ServiceFee>0</ServiceFee>",
        '  <Contact ContactType="Borrower">',
        f"    <FirstName>{_xml_escape(order['borrower_first'])}</FirstName>",
        f"    <LastName>{_xml_escape(order['borrower_last'])}</LastName>",
        f"    <DaytimePhone>{_xml_escape(order['borrower_phone'])}</DaytimePhone>",
        f"    <EmailAddress>{_xml_escape(order['borrower_email'])}</EmailAddress>",
        "  </Contact>",
        f"  <TestTransaction>{'true' if test_transaction else 'false'}</TestTransaction>",
        "  <RushOrder>false</RushOrder>",
        "  <EstimatedValue>0</EstimatedValue>",
        "  <PropertyOccupancy>Owner</PropertyOccupancy>",
        "</AcuityOrder>",
    ]
    return "\n".join(parts)


def basic_auth_header(username: str, password: str) -> str:
    raw = f"{username}:{password}".encode("utf-8")
    return "Basic " + base64.b64encode(raw).decode("ascii")


def require_configured(cfg: dict) -> None:
    missing = [k for k, v in cfg.items() if v == "TBD"]
    if missing:
        print(f"ERROR: SANDBOX values still TBD: {missing}", file=sys.stderr)
        print("Set env vars: ACUITY_USERNAME, ACUITY_PASSWORD, ACUITY_SENDER_ID", file=sys.stderr)
        print("(URL, RecipientID, ProductCode have working defaults.)", file=sys.stderr)
        sys.exit(2)


def do_request(method: str, url: str, body: bytes | None, headers: dict) -> None:
    req = urlrequest.Request(url, data=body, method=method, headers=headers)
    ctx = ssl.create_default_context()
    try:
        with urlrequest.urlopen(req, timeout=60, context=ctx) as resp:
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
    xml = build_acuity_order_xml(SANDBOX, SAMPLE_ORDER, test_transaction=True)
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
    # Doesn't require credentials — uses TBD placeholders if env vars unset.
    xml = build_acuity_order_xml(SANDBOX, SAMPLE_ORDER, test_transaction=True)
    print(xml)
    print(f"\nPartnerReferenceNumber: {SAMPLE_ORDER['partner_reference_number']}")
    print(f"Endpoint:              {SANDBOX['base_url']}")
    tbds = [k for k, v in SANDBOX.items() if v == "TBD"]
    if tbds:
        print(f"\n(Note: env vars not set for: {tbds} — fine for dry-run, required for place-order)")


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
