# AcuityIntegration - Project Configuration

## Project Overview

**Display Name:** Acuity Integration  
**Folder Name:** AcuityIntegration  
**GitHub Repo:** OpteonUSA/AcuityIntegration  
**Owner:** Sal/Brett  
**Parent Project:** AlternativeProductsRouter  

Acuity (ClearValue Consulting) integration for PDR/PDC alternative valuation products. Child flow under AlternativeProductsRouter.

## Architecture

Two-flow async design:
- **Outbound child flow:** Called by AlternativeProductsRouter, builds AcuityOrder XML, POSTs to Acuity, returns acknowledgement
- **Inbound standalone flow:** HTTP trigger receives AcuityReport from Acuity, extracts base64 PDF, uploads to JaroDesk, tags & delivers

## Acuity API Details

- **Protocol:** XML over HTTPS (TLS 1.2)
- **Auth:** HTTP Basic Auth (`Authorization: Basic [Base64(user:pass)]`)
- **Framework Spec:** https://providers.clearvalueconsulting.com/AcuityIntegrationFramework.html
- **Schema Package:** v6.4.0 (XSD)
- **Key message types:** AcuityOrder (out), AcuityAcknowledgement, AcuityReport (in)

## Key Constraints

1. **Async delivery:** Results come back hours/days later - cannot wait in same flow run
2. **XML format:** Must construct XML via string concatenation/Compose (no native PA XML builder)
3. **Base64 documents:** Completed reports are base64-encoded in XML, can be up to 100MB
4. **PartnerReferenceNumber:** Use JaroDesk order ID as the tracking key between outbound/inbound
5. **Order mapping storage:** Need persistent storage (SharePoint list or Dataverse) to link inbound messages back to JaroDesk orders

## Environment Variables (Power Automate)

| Variable | Dev | Prod |
|----------|-----|------|
| `AcuityBaseUrl` | TBD (sandbox) | TBD |
| `AcuitySenderID` | TBD | TBD |
| `AcuityRecipientID` | TBD | TBD |
| `AcuityUsername` | (env var) | (env var) |
| `AcuityPassword` | (env var) | (env var) |

## Related Projects

- **AlternativeProductsRouter** - Parent router that dispatches to this child flow
- **FloodCert** - Sibling child flow (AFR Services, sync JSON)
- **magellan_integrations** - Sibling pattern (Magellan AVM, sync XML)
