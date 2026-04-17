"""
Acuity Integration - Power Automate Solution Generator

Generates TWO importable Power Automate Solution packages (.zip):

  1. Acuity Outbound (Child Flow)
     Manual trigger (called by AlternativeProductsRouter)
     → Build AcuityOrder XML → POST to Acuity → Parse acknowledgement → Return result

  2. Acuity Inbound (Standalone Flow)
     HTTP trigger (Acuity POSTs completed report)
     → Parse AcuityReport XML → Extract base64 PDF → Upload to JaroDesk → Tag & deliver

Both flows use Compose placeholders to demonstrate expected inputs/outputs
before real API wiring.
"""

import os
import re
import sys

# ---------------------------------------------------------------------------
# Path setup
# ---------------------------------------------------------------------------
CURSOR_TOOLS_DIR = os.path.join(
    os.path.expanduser("~"),
    "OneDrive - Opteon",
    "Documents - Business Excellence",
    "Continuous Improvement",
    "Automations",
    "Cursor Tools",
)
PA_FLOW_GENERATOR_MAIN = os.path.join(
    CURSOR_TOOLS_DIR,
    "tools",
    "pa-flow-generator",
    "main",
)
sys.path.insert(0, PA_FLOW_GENERATOR_MAIN)

from solution_builder import SolutionBuilder

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
PUBLISHER_NAME = "SalvatoreVacanti"
PUBLISHER_PREFIX = "acuity"
VERSION_BASE = (1, 0, 0)
RELEASE_DIR = os.path.join(os.path.dirname(__file__), "release")

# Pinned flow IDs (stable across re-generations)
OUTBOUND_FLOW_ID = "b1a2c3d4-e5f6-7890-abcd-ef1234567890"
INBOUND_FLOW_ID = "c2b3d4e5-f6a7-8901-bcde-f12345678901"


# ---------------------------------------------------------------------------
# Versioning
# ---------------------------------------------------------------------------
def _next_version(solution_name: str) -> tuple:
    """Return next semantic version and output zip path."""
    os.makedirs(RELEASE_DIR, exist_ok=True)
    major, minor, build = VERSION_BASE
    prefix = f"{solution_name}_{major}_{minor}_{build}_"
    pattern = re.compile(re.escape(prefix) + r"(\d+)_unmanaged\.zip$")
    max_patch = -1
    old_files = []
    for fn in os.listdir(RELEASE_DIR):
        m = pattern.match(fn)
        if m:
            patch = int(m.group(1))
            if patch > max_patch:
                max_patch = patch
            old_files.append(os.path.join(RELEASE_DIR, fn))
    next_patch = max_patch + 1
    version_str = f"{major}.{minor}.{build}.{next_patch}"
    out_name = f"{prefix}{next_patch}_unmanaged.zip"
    out_path = os.path.join(RELEASE_DIR, out_name)
    for fp in old_files:
        try:
            os.remove(fp)
        except OSError:
            pass
    return version_str, out_path


# ===========================================================================
# FLOW 1: Acuity Outbound (Child Flow)
# ===========================================================================
def create_outbound_flow() -> SolutionBuilder:
    """Child flow called by AlternativeProductsRouter to place an order with Acuity."""

    flow = SolutionBuilder(
        flow_name="Acuity Outbound - Place Order",
        solution_name="AcuityOutbound",
        publisher_name=PUBLISHER_NAME,
        publisher_prefix=PUBLISHER_PREFIX,
        description=(
            "Child flow: receives order details from AlternativeProductsRouter, "
            "builds AcuityOrder XML, POSTs to Acuity, returns acknowledgement result."
        ),
        connection_reference_scope="shared",
    )

    # -------------------------------------------------------------------
    # Environment variables
    # -------------------------------------------------------------------
    flow.add_environment_variable(
        schema_name="acuity_BaseUrl",
        display_name="Acuity Base URL",
        default_value="https://sandbox.clearvalueconsulting.com",
        description="Acuity API endpoint URL (sandbox or production).",
    )
    base_url_param = flow.environment_parameter_name(
        "Acuity Base URL", "acuity_BaseUrl"
    )

    flow.add_environment_variable(
        schema_name="acuity_Username",
        display_name="Acuity Username",
        default_value="",
        description="Acuity HTTP Basic Auth username.",
    )
    username_param = flow.environment_parameter_name(
        "Acuity Username", "acuity_Username"
    )

    flow.add_environment_variable(
        schema_name="acuity_Password",
        display_name="Acuity Password",
        default_value="",
        description="Acuity HTTP Basic Auth password.",
    )
    password_param = flow.environment_parameter_name(
        "Acuity Password", "acuity_Password"
    )

    flow.add_environment_variable(
        schema_name="acuity_SenderID",
        display_name="Acuity SenderID",
        default_value="OPTEON",
        description="SenderID for Acuity XML messages (identifies Opteon).",
    )
    sender_param = flow.environment_parameter_name(
        "Acuity SenderID", "acuity_SenderID"
    )

    flow.add_environment_variable(
        schema_name="acuity_RecipientID",
        display_name="Acuity RecipientID",
        default_value="ACUITY",
        description="RecipientID for Acuity XML messages (identifies Acuity).",
    )
    recipient_param = flow.environment_parameter_name(
        "Acuity RecipientID", "acuity_RecipientID"
    )

    flow.add_environment_variable(
        schema_name="acuity_ProductCode",
        display_name="Acuity Product Code",
        default_value="PDR",
        description="Default Acuity product code for PDR/PDC orders.",
    )
    product_param = flow.environment_parameter_name(
        "Acuity Product Code", "acuity_ProductCode"
    )

    # -------------------------------------------------------------------
    # Trigger: Manual (child flow inputs from router)
    # -------------------------------------------------------------------
    flow.add_manual_trigger(inputs={
        "OrderID": {
            "type": "string",
            "description": "JaroDesk order ID",
            "required": True,
        },
        "CustomerID": {
            "type": "string",
            "description": "JaroDesk customer ID",
            "required": True,
        },
        "BorrowerFirstName": {
            "type": "string",
            "description": "Borrower first name",
            "required": True,
        },
        "BorrowerLastName": {
            "type": "string",
            "description": "Borrower last name",
            "required": True,
        },
        "PropertyAddress": {
            "type": "string",
            "description": "Subject property street address",
            "required": True,
        },
        "PropertyCity": {
            "type": "string",
            "description": "Subject property city",
            "required": True,
        },
        "PropertyState": {
            "type": "string",
            "description": "Subject property state (2-letter)",
            "required": True,
        },
        "PropertyZip": {
            "type": "string",
            "description": "Subject property zip code",
            "required": True,
        },
        "PropertyType": {
            "type": "string",
            "description": "Property type (e.g. SingleFamilyResidence)",
            "required": False,
        },
        "LoanNumber": {
            "type": "string",
            "description": "Loan number",
            "required": False,
        },
        "LoanType": {
            "type": "string",
            "description": "Loan type (Conventional, FHA, VA, etc.)",
            "required": False,
        },
        "LoanPurpose": {
            "type": "string",
            "description": "Loan purpose (Purchase, Refinance, etc.)",
            "required": False,
        },
        "SalesPrice": {
            "type": "string",
            "description": "Sales price",
            "required": False,
        },
        "BorrowerPhone": {
            "type": "string",
            "description": "Borrower daytime phone",
            "required": False,
        },
        "SessionToken": {
            "type": "string",
            "description": "JaroDesk session token (for future file upload use)",
            "required": False,
        },
    })

    # -------------------------------------------------------------------
    # Variables
    # -------------------------------------------------------------------
    flow.add_initialize_variable(
        "Init_Success", "Success", "boolean", False
    )
    flow.add_initialize_variable(
        "Init_ErrorMessage", "ErrorMessage", "string", "",
        ["Init_Success"],
    )
    flow.add_initialize_variable(
        "Init_AcuityOrderID", "AcuityOrderID", "string", "",
        ["Init_ErrorMessage"],
    )

    last_var = "Init_AcuityOrderID"

    # -------------------------------------------------------------------
    # Step 1: Build AcuityOrder XML
    # Uses concat() to construct XML from trigger inputs + env vars
    # -------------------------------------------------------------------
    xml_expr = (
        "@concat("
        "'<?xml version=\"1.0\" encoding=\"utf-8\"?>"
        "<AcuityOrder xmlns:xsi=\"http://www.w3.org/2001/XMLSchema-instance\">"
        "<SenderID>', "
        f"parameters('{sender_param}'), "
        "'</SenderID>"
        "<RecipientID>', "
        f"parameters('{recipient_param}'), "
        "'</RecipientID>"
        "<MessageDate>', "
        "utcNow('o'), "
        "'</MessageDate>"
        "<PartnerReferenceNumber>', "
        "triggerBody()?['OrderID'], "
        "'</PartnerReferenceNumber>"
        "<LineItemNumber>1</LineItemNumber>"
        "<ProductCode>', "
        f"parameters('{product_param}'), "
        "'</ProductCode>"
        "<BillingType>Invoice</BillingType>"
        "<Loan>"
        "<LoanType>', "
        "coalesce(triggerBody()?['LoanType'], 'Conventional'), "
        "'</LoanType>"
        "<LoanPurpose>', "
        "coalesce(triggerBody()?['LoanPurpose'], 'Purchase'), "
        "'</LoanPurpose>"
        "<LoanNumber>', "
        "coalesce(triggerBody()?['LoanNumber'], ''), "
        "'</LoanNumber>"
        "</Loan>"
        "<SubjectProperty>"
        "<Address1>', "
        "replace(replace(replace(triggerBody()?['PropertyAddress'], '&', '&amp;'), '<', '&lt;'), '>', '&gt;'), "
        "'</Address1>"
        "<City>', "
        "triggerBody()?['PropertyCity'], "
        "'</City>"
        "<State>', "
        "triggerBody()?['PropertyState'], "
        "'</State>"
        "<PostalCode>', "
        "triggerBody()?['PropertyZip'], "
        "'</PostalCode>"
        "<SalesPrice>', "
        "coalesce(triggerBody()?['SalesPrice'], '0'), "
        "'</SalesPrice>"
        "<PropertyType>', "
        "coalesce(triggerBody()?['PropertyType'], 'SingleFamilyResidence'), "
        "'</PropertyType>"
        "</SubjectProperty>"
        "<ServiceFee>0</ServiceFee>"
        "<Contact ContactType=\"Borrower\">"
        "<FirstName>', "
        "triggerBody()?['BorrowerFirstName'], "
        "'</FirstName>"
        "<LastName>', "
        "triggerBody()?['BorrowerLastName'], "
        "'</LastName>"
        "<DaytimePhone>', "
        "coalesce(triggerBody()?['BorrowerPhone'], ''), "
        "'</DaytimePhone>"
        "</Contact>"
        "<TestTransaction>false</TestTransaction>"
        "</AcuityOrder>')"
    )
    flow.add_compose("Compose_-_AcuityOrder_XML", xml_expr, [last_var])

    # -------------------------------------------------------------------
    # Step 2: Build Basic Auth header
    # -------------------------------------------------------------------
    auth_expr = (
        "@concat('Basic ', "
        f"base64(concat(parameters('{username_param}'), ':', parameters('{password_param}'))))"
    )
    flow.add_compose(
        "Compose_-_BasicAuth_Header", auth_expr, [last_var]
    )

    # -------------------------------------------------------------------
    # Step 3: POST to Acuity (placeholder - Compose demonstrates output)
    # -------------------------------------------------------------------
    # PLACEHOLDER: Simulates the HTTP POST and Acuity's AcuityAcknowledgement response
    # When ready to go live, replace this Compose with an HTTP action:
    #   flow.add_http("HTTP_-_POST_AcuityOrder", "POST",
    #       uri=f"@parameters('{base_url_param}')",
    #       headers={"Content-Type": "text/xml", "Authorization": auth_expr},
    #       body="@outputs('Compose_-_AcuityOrder_XML')",
    #       after=["Compose_-_AcuityOrder_XML", "Compose_-_BasicAuth_Header"])
    placeholder_ack = (
        "'<?xml version=\"1.0\" encoding=\"utf-8\"?>"
        "<AcuityAcknowledgement>"
        "<SenderID>ACUITY</SenderID>"
        "<RecipientID>OPTEON</RecipientID>"
        "<MessageDate>2026-04-17T12:00:00.0000000-07:00</MessageDate>"
        "<System>Acuity</System>"
        "<MessageVersion>6.4</MessageVersion>"
        "<PartnerReferenceNumber>PLACEHOLDER-ORDER-123</PartnerReferenceNumber>"
        "<LineItemNumber>1</LineItemNumber>"
        "<Success>true</Success>"
        "</AcuityAcknowledgement>'"
    )
    flow.add_compose(
        "Compose_-_PLACEHOLDER_Acuity_Response",
        placeholder_ack,
        ["Compose_-_AcuityOrder_XML", "Compose_-_BasicAuth_Header"],
    )

    # -------------------------------------------------------------------
    # Step 4: Parse the acknowledgement XML to JSON
    # -------------------------------------------------------------------
    flow.add_compose(
        "Compose_-_Ack_As_JSON",
        "@json(xml(outputs('Compose_-_PLACEHOLDER_Acuity_Response')))",
        ["Compose_-_PLACEHOLDER_Acuity_Response"],
    )

    # -------------------------------------------------------------------
    # Step 5: Extract Success flag
    # -------------------------------------------------------------------
    flow.add_compose(
        "Compose_-_Ack_Success",
        "@outputs('Compose_-_Ack_As_JSON')?['AcuityAcknowledgement']?['Success']",
        ["Compose_-_Ack_As_JSON"],
    )

    # -------------------------------------------------------------------
    # Step 6: Check if Acuity accepted the order
    # -------------------------------------------------------------------
    flow.add_condition(
        name="Condition_-_Order_Accepted",
        expression={
            "and": [
                {"equals": [
                    "@outputs('Compose_-_Ack_Success')",
                    "true",
                ]}
            ]
        },
        if_true_actions={
            "Set_Success_True": {
                "type": "SetVariable",
                "inputs": {
                    "name": "Success",
                    "value": True,
                },
            },
            "Set_AcuityOrderID": {
                "type": "SetVariable",
                "inputs": {
                    "name": "AcuityOrderID",
                    "value": "@outputs('Compose_-_Ack_As_JSON')?['AcuityAcknowledgement']?['PartnerReferenceNumber']",
                },
                "runAfter": {"Set_Success_True": ["Succeeded"]},
            },
        },
        if_false_actions={
            "Set_ErrorMessage_From_Ack": {
                "type": "SetVariable",
                "inputs": {
                    "name": "ErrorMessage",
                    "value": "@concat('Acuity rejected order. Error: ', coalesce(outputs('Compose_-_Ack_As_JSON')?['AcuityAcknowledgement']?['Error']?['ErrorCode'], 'Unknown'), ' - ', coalesce(outputs('Compose_-_Ack_As_JSON')?['AcuityAcknowledgement']?['Error']?['ErrorMessage'], 'No details'))",
                },
            },
        },
        after=["Compose_-_Ack_Success"],
    )

    # -------------------------------------------------------------------
    # Step 7: Return result to router
    # -------------------------------------------------------------------
    flow.add_response(
        name="Response_-_Return_Result",
        status_code=200,
        body={
            "Success": "@variables('Success')",
            "FileUploaded": False,
            "ErrorMessage": "@variables('ErrorMessage')",
            "ProviderOrderID": "@variables('AcuityOrderID')",
        },
        headers={"Content-Type": "application/json"},
        after=["Condition_-_Order_Accepted"],
    )

    return flow


# ===========================================================================
# FLOW 2: Acuity Inbound (Standalone - receives completed reports)
# ===========================================================================
def create_inbound_flow() -> SolutionBuilder:
    """Standalone flow: HTTP trigger receives AcuityReport from Acuity, uploads PDF to JaroDesk."""

    flow = SolutionBuilder(
        flow_name="Acuity Inbound - Receive Report",
        solution_name="AcuityInbound",
        publisher_name=PUBLISHER_NAME,
        publisher_prefix=PUBLISHER_PREFIX,
        description=(
            "Standalone flow: receives AcuityReport XML from Acuity via HTTP POST, "
            "extracts base64 PDF, uploads to JaroDesk order, tags and delivers."
        ),
        connection_reference_scope="shared",
    )

    # -------------------------------------------------------------------
    # Environment variables
    # -------------------------------------------------------------------
    flow.add_environment_variable(
        schema_name="acuity_SenderID",
        display_name="Acuity SenderID",
        default_value="OPTEON",
        description="Expected SenderID in inbound messages (for validation).",
    )
    sender_param = flow.environment_parameter_name(
        "Acuity SenderID", "acuity_SenderID"
    )

    # -------------------------------------------------------------------
    # Trigger: HTTP Request (Acuity POSTs to this endpoint)
    # -------------------------------------------------------------------
    flow.add_http_request_trigger(method="POST")
    # Remove default schema - we'll parse XML manually
    flow.triggers["When_a_HTTP_request_is_received"]["inputs"].pop("schema", None)
    flow.triggers["When_a_HTTP_request_is_received"]["inputs"][
        "triggerAuthenticationType"
    ] = "All"

    # -------------------------------------------------------------------
    # Variables (root level)
    # -------------------------------------------------------------------
    flow.add_initialize_variable(
        "Init_MessageType", "MessageType", "string", ""
    )
    flow.add_initialize_variable(
        "Init_PartnerRefNum", "PartnerRefNum", "string", "",
        ["Init_MessageType"],
    )
    flow.add_initialize_variable(
        "Init_DocumentBase64", "DocumentBase64", "string", "",
        ["Init_PartnerRefNum"],
    )
    flow.add_initialize_variable(
        "Init_RunStatus", "RunStatus", "string", "Started",
        ["Init_DocumentBase64"],
    )
    flow.add_initialize_variable(
        "Init_ErrorMessage", "ErrorMessage", "string", "",
        ["Init_RunStatus"],
    )

    last_var = "Init_ErrorMessage"

    # -------------------------------------------------------------------
    # Step 1: Respond immediately (200 OK) to Acuity
    # Acuity expects a synchronous acknowledgement
    # -------------------------------------------------------------------
    ack_xml = (
        "'<?xml version=\"1.0\" encoding=\"utf-8\"?>"
        "<AcuityAcknowledgement>"
        "<SenderID>OPTEON</SenderID>"
        "<RecipientID>ACUITY</RecipientID>"
        "<MessageDate>', utcNow('o'), '</MessageDate>"
        "<System>Opteon</System>"
        "<MessageVersion>6.4</MessageVersion>"
        "<Success>true</Success>"
        "</AcuityAcknowledgement>'"
    )
    flow.add_compose(
        "Compose_-_Ack_Response_XML",
        f"@concat({ack_xml})",
        [last_var],
    )

    flow.add_response(
        name="Response_-_Ack_To_Acuity",
        status_code=200,
        body="@outputs('Compose_-_Ack_Response_XML')",
        headers={"Content-Type": "text/xml"},
        after=["Compose_-_Ack_Response_XML"],
    )

    # -------------------------------------------------------------------
    # Step 2: Parse the inbound XML to JSON
    # -------------------------------------------------------------------
    flow.add_compose(
        "Compose_-_Raw_Body",
        "@triggerBody()",
        ["Response_-_Ack_To_Acuity"],
    )

    flow.add_compose(
        "Compose_-_Inbound_As_JSON",
        "@json(xml(outputs('Compose_-_Raw_Body')))",
        ["Compose_-_Raw_Body"],
    )

    # -------------------------------------------------------------------
    # Step 3: Detect message type
    # The root XML element name tells us the message type.
    # We check for the most common types.
    # -------------------------------------------------------------------

    # PLACEHOLDER: Simulated inbound AcuityReport for demonstration
    placeholder_report = (
        "'<?xml version=\"1.0\" encoding=\"utf-8\"?>"
        "<AcuityReport>"
        "<SenderID>ACUITY</SenderID>"
        "<RecipientID>OPTEON</RecipientID>"
        "<MessageDate>2026-04-17T14:30:00.0000000-07:00</MessageDate>"
        "<PartnerReferenceNumber>12345</PartnerReferenceNumber>"
        "<LineItemNumber>1</LineItemNumber>"
        "<Correction>false</Correction>"
        "<Fees>"
        "<VendorFee>250</VendorFee>"
        "<ManagementFee>50</ManagementFee>"
        "<TotalFees>300</TotalFees>"
        "</Fees>"
        "<Document DocumentType=\"AppraisalReport\">"
        "<MimeType>application/pdf</MimeType>"
        "<Content>JVBERi0xLjQKMSAwIG9iago8PCAvVHlwZSAvQ2F0YWxvZwovUGFnZXMgMiAwIFIKPj4KZW5kb2Jq</Content>"
        "</Document>"
        "</AcuityReport>'"
    )
    flow.add_compose(
        "Compose_-_PLACEHOLDER_Sample_AcuityReport",
        placeholder_report,
        ["Compose_-_Inbound_As_JSON"],
    )

    # Demonstrate JSON structure after xml() -> json() conversion
    flow.add_compose(
        "Compose_-_PLACEHOLDER_Parsed_Report",
        "@json(xml(outputs('Compose_-_PLACEHOLDER_Sample_AcuityReport')))",
        ["Compose_-_PLACEHOLDER_Sample_AcuityReport"],
    )

    # -------------------------------------------------------------------
    # Step 4: Determine message type from JSON keys
    # After xml()->json(), root element becomes a top-level key
    # -------------------------------------------------------------------
    flow.add_condition(
        name="Condition_-_Is_AcuityReport",
        expression={
            "and": [
                {"not": {"equals": [
                    "@coalesce(outputs('Compose_-_Inbound_As_JSON')?['AcuityReport'], null)",
                    "@null",
                ]}}
            ]
        },
        if_true_actions={
            "Set_MessageType_Report": {
                "type": "SetVariable",
                "inputs": {
                    "name": "MessageType",
                    "value": "AcuityReport",
                },
            },
            "Set_PartnerRefNum_From_Report": {
                "type": "SetVariable",
                "inputs": {
                    "name": "PartnerRefNum",
                    "value": "@outputs('Compose_-_Inbound_As_JSON')?['AcuityReport']?['PartnerReferenceNumber']",
                },
                "runAfter": {"Set_MessageType_Report": ["Succeeded"]},
            },
            "Set_DocumentBase64": {
                "type": "SetVariable",
                "inputs": {
                    "name": "DocumentBase64",
                    "value": "@outputs('Compose_-_Inbound_As_JSON')?['AcuityReport']?['Document']?['Content']",
                },
                "runAfter": {"Set_PartnerRefNum_From_Report": ["Succeeded"]},
            },
        },
        if_false_actions={
            "Set_MessageType_Other": {
                "type": "SetVariable",
                "inputs": {
                    "name": "MessageType",
                    "value": "Other",
                },
            },
            "Compose_-_Log_Non_Report_Message": {
                "type": "Compose",
                "inputs": "@concat('Received non-report Acuity message. Full JSON: ', string(outputs('Compose_-_Inbound_As_JSON')))",
                "runAfter": {"Set_MessageType_Other": ["Succeeded"]},
            },
        },
        after=["Compose_-_PLACEHOLDER_Parsed_Report"],
    )

    # -------------------------------------------------------------------
    # Step 5: Process AcuityReport - extract and demonstrate upload path
    # -------------------------------------------------------------------
    flow.add_condition(
        name="Condition_-_Process_Report",
        expression={
            "and": [
                {"equals": ["@variables('MessageType')", "AcuityReport"]},
                {"not": {"equals": ["@variables('DocumentBase64')", ""]}}
            ]
        },
        if_true_actions={
            # PLACEHOLDER: Demonstrates the data available for JaroDesk upload
            "Compose_-_PLACEHOLDER_Upload_Summary": {
                "type": "Compose",
                "inputs": "@concat("
                    "'Ready to upload to JaroDesk:', "
                    "'\\nPartnerReferenceNumber (JaroDesk OrderID): ', variables('PartnerRefNum'), "
                    "'\\nDocument size (base64 chars): ', string(length(variables('DocumentBase64'))), "
                    "'\\nNext steps:', "
                    "'\\n  1. GET /v1/order/{OrderID}/file/upload (signed URL)', "
                    "'\\n  2. PUT to S3 signed URL with decoded PDF', "
                    "'\\n  3. POST /v1/order/{OrderID}/file/attach', "
                    "'\\n  4. POST /v1/order/{OrderID}/tag (Automation)', "
                    "'\\n  5. POST /v1/order/{OrderID}/workflow/send (deliver)')",
            },
            "Set_RunStatus_Success": {
                "type": "SetVariable",
                "inputs": {
                    "name": "RunStatus",
                    "value": "ReportReceived",
                },
                "runAfter": {"Compose_-_PLACEHOLDER_Upload_Summary": ["Succeeded"]},
            },
        },
        if_false_actions={
            "Set_RunStatus_Skipped": {
                "type": "SetVariable",
                "inputs": {
                    "name": "RunStatus",
                    "value": "Skipped_NotAReport",
                },
            },
        },
        after=["Condition_-_Is_AcuityReport"],
    )

    # -------------------------------------------------------------------
    # Step 6: Final summary compose (demonstrates all extracted data)
    # -------------------------------------------------------------------
    flow.add_compose(
        "Compose_-_Final_Summary",
        "@concat("
        "'Acuity Inbound Processing Complete', "
        "'\\nMessage Type: ', variables('MessageType'), "
        "'\\nPartner Ref: ', variables('PartnerRefNum'), "
        "'\\nRun Status: ', variables('RunStatus'), "
        "'\\nHas Document: ', string(not(equals(variables('DocumentBase64'), ''))))",
        ["Condition_-_Process_Report"],
    )

    return flow


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> None:
    print("=" * 60)
    print("Acuity Integration - Solution Generator")
    print("=" * 60)

    # --- Outbound flow ---
    print("\n[1/2] Generating Acuity Outbound (Child Flow)...")
    version_out, path_out = _next_version("AcuityOutbound")
    outbound = create_outbound_flow()
    outbound.save_solution(
        path_out, existing_flow_id=OUTBOUND_FLOW_ID, version=version_out
    )
    print(f"  -> {path_out}  (v{version_out})")

    # --- Inbound flow ---
    print("\n[2/2] Generating Acuity Inbound (Standalone Flow)...")
    version_in, path_in = _next_version("AcuityInbound")
    inbound = create_inbound_flow()
    inbound.save_solution(
        path_in, existing_flow_id=INBOUND_FLOW_ID, version=version_in
    )
    print(f"  -> {path_in}  (v{version_in})")

    print("\n" + "=" * 60)
    print("Done! Import both .zip files into Power Automate Solutions.")
    print("=" * 60)


if __name__ == "__main__":
    main()
