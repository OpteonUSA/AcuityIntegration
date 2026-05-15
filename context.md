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

> **There is no separate sandbox environment.** Confirmed by Valor 2026-05-14: Opteon and Valor both operate in PROD on both sides of the integration. The same endpoint, credentials, and account IDs apply across our DEV/UAT/PROD Power Automate environments. Each Acuity order sent — including test orders — is a real Valor order. Treat with care (real billing, real vendor dispatch).

| Setting | Value | Notes |
|---------|-------|-------|
| Outbound POST URL | `https://clients.valorvaluations.com/adapters/Integration/Acuity` | Single endpoint for all PA environments |
| Master Client ID | 56135 | Valor-side account ID; **NOT on the wire** (see note) |
| Branch ID | 1055 | Valor-side account ID; **NOT on the wire** (see note) |
| SenderID (us → Valor) | `OPTEONAMC` | Confirmed Valor 2026-05-04; supersedes earlier `OPTEON`. Used in outbound XML + inbound ack |
| RecipientID (us → Valor outbound) | `VALOR` | Used in AcuityOrder XML body |
| RecipientID (us → Valor inbound ack) | `ACUITY` | Currently sent in inbound AcuityAcknowledgement; pending confirmation against more captured examples |
| Username | (env var / Dataverse `cre4a_username`) | |
| Password | (env var / Dataverse `cre4a_password`) | |

**Note on MasterClientID + BranchID (RESOLVED 2026-05-14, Valor verbal):**

Confirmed: Master/Branch are Valor-side account identifiers only and **do not appear on the wire in any form**. Identity binding is Basic Auth + SenderID alone. The earlier hypothesis (pre-3003) was correct all along — the 3003 detour was caused by the wrong SenderID value (`OPTEON` vs the correct `OPTEONAMC`), not a missing Master/Branch field. The 6.4.0 XSD has no element for either ID, and Valor explicitly stated they are not needed on outbound.

### Product Code (Valor) — Single ProductCode, GSE-program-paired identifier

**Confirmed by Valor 2026-05-14 (refined from 2026-05-04):** there is **only one ProductCode** for both PDR and PDC. The differentiator is which GSE program drove the order, expressed via the `ForeignOrderIdentifier` element. Both products carry an identifier — they're never identifier-less, and they're never both populated.

| Product | GSE Program | Acuity ProductCode | ForeignOrderIdentifier |
|---------|-------------|--------------------|------------------------|
| PDR | Freddie Mac **ACE** | `9` | `Type="FreddieMacLPAKey"`, ID = LPA Key from JaroDesk |
| PDC | Fannie Mae **ValueAcceptance** | `9` | `Type="FannieMaeCaseFileID"`, ID = DU CaseFile ID from JaroDesk |

**Mutually exclusive:** never both. One identifier always present.

**Wire placement** — `ForeignOrderIdentifier` element on `AcuityOrder`. Per the 6.4.0 XSD, `ForeignOrderIdentifier.Type` is an `AlternateIDType` enum with these values (only the two below apply to our integration):
- `FreddieMacLPAKey` ← ACE / PDR
- `FannieMaeCaseFileID` ← ValueAcceptance / PDC
- `GSEDocFileID`, `FHADocFileID`, `FannieMaePropertyDataID` (defined in XSD but not used by Valor for our products)

Element is repeating (`maxOccurs="unbounded"`) per XSD, but per Valor 2026-05-14 we emit exactly one per order.

Example for PDR:
```xml
<ForeignOrderIdentifier ID="AN815824" Type="FreddieMacLPAKey" />
```

Example for PDC:
```xml
<ForeignOrderIdentifier ID="AN815824" Type="FannieMaeCaseFileID" />
```

**JaroDesk source for the identifier values:**
- Endpoint: `GET https://api.jarodesk.com/v1/order/{order_id}/incremental`
- Path: `body.details.details.lpaKey` and `body.details.details.duCaseFileId`
- Note: JaroDesk may populate both fields with the same value on the same order. Use the router's `pdr` vs `pdc` case as the authority for which identifier to emit (PDR → use `lpaKey`, PDC → use `duCaseFileId`).

**Implication for Acuity Outbound Child design (v36 of the generator):**
- ProductCode is hardcoded to `9` in the outbound XML construction. No Dataverse lookup needed for product.
- The child accepts `FreddieMacLPAKey` + `FannieMaeCaseFileID` as optional trigger inputs.
- The child emits one `<ForeignOrderIdentifier>` element via conditional Compose action: LPA Key wins if both populated; if neither, no element emitted (preserves backward compatibility).
- Router-side work (queued for v37): add `HTTP_-_Get_Order_Incremental` action; populate router variables `FreddieMacLPAKey` + `FannieMaeCaseFileID` from the incremental endpoint; pass them through PDR/PDC case body invocations.

### Data Mapping: JaroDesk to Acuity

| JaroDesk Field | Acuity XML Field | Notes |
|----------------|-----------------|-------|
| Order ID | `PartnerReferenceNumber` | Tracking key for async matching |
| (none — hardcoded) | `ProductCode` | Always `9` per Valor 2026-05-14; no lookup |
| Loan type | `Loan > LoanType` | Enum passes 1:1, no transformation (Valor 2026-05-14) |
| Loan purpose | `Loan > LoanPurpose` | Enum passes 1:1, no transformation (Valor 2026-05-14) |
| Loan number | `Loan > LoanNumber` | Pass-through |
| `incremental.body.details.details.lpaKey` | `ForeignOrderIdentifier ID="..." Type="FreddieMacLPAKey"` | PDR/ACE only |
| `incremental.body.details.details.duCaseFileId` | `ForeignOrderIdentifier ID="..." Type="FannieMaeCaseFileID"` | PDC/ValueAcceptance only |
| Property address | `SubjectProperty > Address1/City/State/PostalCode` | Direct mapping |
| Property type | `SubjectProperty > PropertyType` | Enum passes 1:1, no transformation (Valor 2026-05-14) |
| Borrower name | `Contact[@ContactType="Borrower"]` | Split First/Last; ContactType enum passes 1:1 |
| Borrower phone | `Contact > DaytimePhone` | Pass-through |
| Entry contact (JaroDesk) | `PropertyAccess` | Valor 2026-05-14 |

**Removed from prior mapping:**
- ~~Sales price → SubjectProperty.SalesPrice~~ — Valor confirmed 2026-05-14 the field is **not consumed**; do not emit.

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

Valor returns errors in **two distinct shapes** depending on which validation layer fired:

1. **Schema/instance validation failure (e.g. enum mismatch):** top-level `<Error>` element, NOT wrapped in `<AcuityAcknowledgement>`:
   ```xml
   <Error>
     <ErrorCode>0500</ErrorCode>
     <ErrorMessage>Instance validation error: 'fakepropertytype' is not a valid value for AcuityPropertyType.</ErrorMessage>
   </Error>
   ```
2. **Business-logic failure inside an accepted envelope:** wrapped as `<AcuityAcknowledgement><Error><ErrorCode/><ErrorMessage/></Error></AcuityAcknowledgement>`. Confirmed live via the May 4 `3003 client profile` rejection.
3. **Auth failure:** HTTP 401, body shape unspecified.

### Known error codes

| Code | Meaning | Response shape | Source |
|------|---------|----------------|--------|
| `0500` | Schema / instance validation failure (e.g. enum mismatch) | Top-level `<Error>` | Valor sample 2026-05-04 |
| `3003` | Client profile cannot be determined (e.g. wrong SenderID) | Wrapped in `<AcuityAcknowledgement>` | Live retest 2026-05-04 (resolved by switching `OPTEON` → `OPTEONAMC`) |
| `3019` | Duplicate `PartnerReferenceNumber` — order already received | Shape TBD (likely wrapped, confirm next occurrence) | Valor verbal 2026-05-14 |

**Handling responsibility for `3019`:** when fired, write a JaroDesk-visible message (note / case event) flagging duplicate detection. Implies an idempotency table (Dataverse, keyed on `PartnerReferenceNumber`) so the outbound flow can know "already sent and acked" before retrying on transient 5xx.

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
