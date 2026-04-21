# AcuityIntegration - Context

## Quick Reference

**Status:** In Progress  
**Owner:** Sal/Brett  
**Created:** April 17, 2026  
**Last Updated:** April 17, 2026

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
- **Sandbox host:** `https://clients.valorvaluations.com` (full POST path TBD)
- **Auth:** HTTP Basic Authentication (Base64-encoded username:password)
- **Protocol:** XML over HTTPS (TLS 1.2)
- **Framework:** [AcuityExchange Integration Framework](https://providers.clearvalueconsulting.com/AcuityIntegrationFramework.html)
- **Schema Version:** v6.4.0

### Key IDs
| Setting | Dev (Sandbox) | Prod |
|---------|---------------|------|
| Base URL | `https://clients.valorvaluations.com` (path TBD) | TBD |
| Master Client ID | 56135 | TBD |
| Branch ID | 1055 | TBD |
| SenderID | TBD | TBD |
| RecipientID | captured (see `tools/CALL_CHECKLIST.md` — gitignored) | TBD |
| Username | captured (env var) | (env var) |
| Password | captured (env var) | (env var) |

### Product Code Mapping (Valor)
| Product | Acuity ProductCode | Prerequisite |
|---------|--------------------|--------------|
| PDC | `9` | (none confirmed) |
| PDR | TBD (pending from ClearValue) | Requires CaseFile **or** LPA findings to be attached/referenced |

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
| AcuityOrder | Outbound | Place new order |
| AcuityAcknowledgement | Response | Synchronous receipt confirmation |
| AcuityOrderAcceptance | Inbound | Vendor accepted order |
| AcuityAssignment | Inbound | Inspector assigned |
| AcuityReport | Inbound | **Completed report with base64 PDF** |
| AcuityDelay | Inbound | Order on hold |
| AcuityCancellation | Inbound/Outbound | Cancellation request |

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
