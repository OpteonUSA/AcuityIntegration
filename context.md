# AcuityIntegration - Context

## Quick Reference

**Status:** Tier 1 unblocked — most ClearValue/Valor questions answered May 4
**Owner:** Sal/Brett
**Created:** April 17, 2026
**Last Updated:** May 4, 2026

---

## Project Summary

This automation integrates JaroDesk with Acuity (ClearValue Consulting) to order and receive PDR (Property Data Report) and PDC (Property Data Collection) alternative valuation products. It operates as a child flow under the AlternativeProductsRouter, using a two-flow async design: one flow places the order, a separate flow receives the completed report when Acuity delivers it.

---

## Data Flow

**Source:** JaroDesk order (via AlternativeProductsRouter webhook)  
**Processing:** Transform JaroDesk order data to AcuityOrder XML, POST to Acuity; receive AcuityReport XML asynchronously, extract base64 PDF  
**Target:** Upload completed PDF back to JaroDesk order, tag & deliver

---

## Technical Details

### Trigger
- **Outbound:** AlternativeProductsRouter child flow call (JaroDesk webhook origin)
- **Inbound:** HTTP trigger (Acuity POSTs completed report to our endpoint)

### Target System API
- **Vendor brand:** Valor Valuations (ClearValue Consulting runs the Acuity framework/platform)
- **Outbound endpoint (us → Valor):** `https://clients.valorvaluations.com/adapters/Integration/Acuity` (confirmed May 4)
- **Inbound endpoint (Valor → us):** ONE PA HTTP-trigger URL we register with Valor; Valor only supports a single outbound URL slot, so re-registering after a solution import (per `feedback_pa_solution_import_webhook_url`) requires updating Valor too
- **Outbound auth (us → Valor):** HTTP Basic Authentication (Base64-encoded username:password)
- **Inbound auth (Valor → us):** **None — Valor does not authenticate itself when posting to us.** Mitigation: validate `SenderID` element on every inbound XML and reject anything not from "VALOR"
- **Protocol:** XML over HTTPS (TLS 1.2 or 1.3)
- **Rate limits:** None advertised, but Valor requires sequential delivery — updates are applied in receive order. Do NOT parallelize order POSTs for the same `PartnerReferenceNumber`
- **Outbound retry (us → Valor):** none on success path; if Valor 5xx's, retry policy is on us. Valor itself retries inbound delivery to us ~3 times (connection establishment) — anything past that is dropped
- **Framework:** [AcuityExchange Integration Framework](https://providers.clearvalueconsulting.com/AcuityIntegrationFramework.html)
- **Schema Version:** v6.4.0

### Key IDs
| Setting | Dev (Sandbox) | Prod |
|---------|---------------|------|
| Outbound POST URL | `https://clients.valorvaluations.com/adapters/Integration/Acuity` | TBD |
| Master Client ID | 56135 (Valor-side account ID — see note below) | TBD |
| Branch ID | 1055 (Valor-side account ID — see note below) | TBD |
| SenderID (us → Valor) | TBD (captured in checklist) | TBD |
| RecipientID (us → Valor) | "VALOR" works; specific Valor RecipientID captured in checklist | TBD |

**Note on MasterClientID + BranchID placement (verified May 4, 2026 against the public 6.4.0 schema package at `https://providers.clearvalueconsulting.com/artifacts/6.4.0.zip`):**

`MasterClientID` and `BranchID` **do not exist as elements anywhere in the AcuityOrder XSD or any other 6.4.0 message schema.** Full element list of `<AcuityOrder>` is captured below. The closest available fields are:

- `CostCenter` (xs:string, optional) — single free-form text field
- `OperationalTag1` / `OperationalTag2` (xs:string, optional) — generic tagging fields
- `InvestorCode` (xs:string, optional)
- `BatchName` (xs:string, optional)
- `ForeignOrderIdentifier` (repeating structured type) — typed Type+Identifier pairs; would cleanly fit a `Type="MasterClientID", Identifier="56135"` shape if Valor wants them on the wire
- `BroadcastRecipient` (repeating structured type)

**Most likely interpretation:** Master Client 56135 and Branch 1055 identify Opteon's account on Valor's side — Basic Auth is the identity binding, and Valor looks up the account internally. We probably do NOT need to embed either value in the AcuityOrder XML.

**Alternative interpretation:** Valor uses a custom extension to the public 6.4.0 schema (`OperationalTag1`, `CostCenter`, or `ForeignOrderIdentifier` are the natural fits). This would not show up in the public XSD.

**Action item for Sal:** Confirm with ClearValue/Valor explicitly: "Does the AcuityOrder XML need to carry MasterClientID and BranchID at all? If yes, in which element?" Until confirmed, the outbound child should ship WITHOUT these fields — Basic Auth is the identity mechanism.
| Username | captured (env var) | (env var) |
| Password | captured (env var) | (env var) |

### Product Code Mapping (Valor)
| Product | Acuity ProductCode | Prerequisite |
|---------|--------------------|--------------|
| PDC | `9` | (none confirmed) |
| PDR | **STILL TBD** (pending from ClearValue as of May 4) | Requires CaseFile **or** LPA findings to be attached/referenced |

**Routing rule:** `LPA or CaseFile` presence on the JaroDesk order drives PDR selection; absence = PDC. Encode this in the router upstream so this flow only receives the already-resolved product code.

### Data Mapping: JaroDesk to Acuity

| JaroDesk Field | Acuity XML Field | Notes |
|----------------|-----------------|-------|
| Order ID | `PartnerReferenceNumber` | Tracking key for async matching |
| Product/Form type | `ProductCode` | Lookup table needed |
| Loan type | `Loan > LoanType` | Enum mapping |
| Loan purpose | `Loan > LoanPurpose` | Enum mapping |
| Loan number | `Loan > LoanNumber` | Pass-through |
| Property address | `SubjectProperty > Address1/City/State/PostalCode` | Direct mapping |
| Property type | `SubjectProperty > PropertyType` | Enum mapping |
| Sales price | `SubjectProperty > SalesPrice` | Pass-through |
| Borrower name | `Contact[@ContactType="Borrower"]` | Split First/Last |
| Borrower phone | `Contact > DaytimePhone` | Pass-through |

### Key Acuity Message Types

| Message | Direction | Purpose |
|---------|-----------|---------|
| AcuityOrder | Outbound | Place new order — full payload |
| AcuityOrderUpdate | Outbound | Update existing order — only changed fields (per Valor, May 4) |
| AcuityAcknowledgement | Response | Synchronous receipt confirmation |
| AcuityOrderAcceptance | Inbound | Vendor accepted order |
| AcuityAssignment | Inbound | Inspector assigned |
| AcuityReport | Inbound | **Completed report with base64 PDF** |
| AcuityDelay | Inbound | Order on hold |
| AcuityCancellation | Inbound/Outbound | Cancellation request |

### Error Response Shapes

Valor returns errors in **two distinct shapes** depending on which validation layer fired (confirmed May 4 via "fakepropertytype" sample):

1. **Schema/instance validation failure (e.g. enum mismatch):** top-level `<Error>` element, NOT wrapped in `<AcuityAcknowledgement>`:
   ```xml
   <Error>
     <ErrorCode>0500</ErrorCode>
     <ErrorMessage>Instance validation error: 'fakepropertytype' is not a valid value for AcuityPropertyType.</ErrorMessage>
   </Error>
   ```
2. **Business-logic failure inside an accepted envelope:** wrapped as `<AcuityAcknowledgement><Error><ErrorCode/><ErrorMessage/></Error></AcuityAcknowledgement>` (assumed; not yet confirmed live).
3. **Auth failure:** HTTP 401, body shape unspecified.

**Implication for outbound child:** the response parser must probe both shapes via coalesce — same pattern as the Magellan AVM Child v33 fix. Current code only reads `AcuityAcknowledgement.Error.*`; needs widening to also read top-level `Error.*` and to fall through to `string(...)` of the full response if neither path resolves. Reference the `feedback_surface_literal_api_errors` shared lesson.

---

## Files

| File | Purpose |
|------|---------|
| `workflow-diagram.html` | Visual workflow diagram showing two-flow architecture |
| `context.md` | Project context and technical details (this file) |
| `memory-bank/10-progress.md` | Progress tracking and session log |
| `kpi.md` | Strategic KPI metrics |
| `README.md` | Project overview and documentation |
| `feasibility-analysis.html` | Initial feasibility analysis |

---

## Dependencies

- **AlternativeProductsRouter** - Parent flow that dispatches PDR/PDC orders to this child
- **JaroDesk API** - Order retrieval, file upload, tagging, delivery
- **Acuity/ClearValue API** - Order placement and report delivery
- **Dataverse TokenCache** - JaroDesk authentication tokens
- **SharePoint or Dataverse** - Order mapping storage (JaroDesk ID <-> Acuity ref)
