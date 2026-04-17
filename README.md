# AcuityIntegration

Acuity (ClearValue Consulting) integration for ordering PDR/PDC alternative valuation products through JaroDesk. Built as a child flow within the [AlternativeProductsRouter](https://github.com/OpteonUSA/AlternativeProductsRouter).

## Overview

This project automates the placement and fulfillment of Property Data Report (PDR) and Property Data Collection (PDC) orders through the AcuityExchange platform. Orders originate in JaroDesk, flow to Acuity for fulfillment, and completed reports are returned and attached to the JaroDesk order.

## Architecture

**Two-flow design** (due to Acuity's asynchronous delivery model):

```
AlternativeProductsRouter (parent)
  |
  +-- Magellan AVM child       (sync)
  +-- AFR Flood Cert child     (sync)
  +-- Acuity PDR/PDC child     (async)
        |
        +-- Outbound flow: places order with Acuity
        +-- Inbound flow:  receives completed report from Acuity
```

- **Outbound Flow:** Triggered by JaroDesk webhook via AlternativeProductsRouter. Transforms order data to AcuityOrder XML, POSTs to Acuity, logs acknowledgement.
- **Inbound Flow:** HTTP trigger endpoint that receives AcuityReport messages. Extracts base64-encoded PDF, uploads to JaroDesk via 3-step file upload, tags and delivers the order.

## Integration Details

| Aspect | Detail |
|--------|--------|
| **Vendor** | Acuity / ClearValue Consulting |
| **Protocol** | XML over HTTPS |
| **Auth** | HTTP Basic Authentication |
| **Products** | PDR, PDC (alternative valuation) |
| **Delivery** | Asynchronous (hours/days) |
| **Framework Spec** | [AcuityExchange Integration Framework](https://providers.clearvalueconsulting.com/AcuityIntegrationFramework.html) |

## Project Files

| File | Purpose |
|------|---------|
| `context.md` | Technical context, data mappings, API details |
| `memory-bank/10-progress.md` | Progress tracking and session log |
| `kpi.md` | Strategic KPI metrics |
| `workflow-diagram.html` | Visual workflow diagram |
| `feasibility-analysis.html` | Initial feasibility analysis |

## Owners

Sal Vacanti / Brett Cowden

## Related Projects

- [AlternativeProductsRouter](https://github.com/OpteonUSA/AlternativeProductsRouter) - Parent router flow
- [FloodCert](https://github.com/OpteonUSA/FloodCert) - Sibling child flow (AFR flood certs)
- [magellan_integrations](https://github.com/OpteonUSA/magellan_integrations) - Sibling pattern (AVM via XML)
