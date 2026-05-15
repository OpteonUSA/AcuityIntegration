# Acuity / Valor Meeting Prep — 2026-05-14

**Attendee (Opteon):** Sal Vacanti
**Vendor:** ClearValue Consulting / Valor Valuations
**Status going in:** Bidirectional sandbox connectivity wire-proven (May 7); JaroDesk side blocked on prereqs; planning to build full Case handling beyond MVP.

Priority key: 🔴 blockers / must-have • 🟡 important, can defer • 🟢 nice to know

---

## 🔴 Blockers — open items from progress.md

1. **MasterClientID `56135` + BranchID `1055` — XML placement.** Already in your consolidated email. Confirm verbally:
   - Do these need to be on the wire at all, or are they bound by Basic Auth + SenderID alone?
   - If on the wire: which element? `ForeignOrderIdentifier` is ruled out by the XSD enum. Remaining candidates: `OperationalTag1/2`, `CostCenter`, `InvestorCode`, `BatchName`, `BroadcastRecipient`, or a Valor-private extension.

2. **Duplicate `PartnerReferenceNumber` behavior in PROD.** Sandbox accepted a re-sent ID without complaint. PROD behavior unknown — reject, idempotently re-ack, or duplicate-create? Drives retry semantics on connection-level failures.

3. **Fast-complete sandbox code.** Need a magic value or product code that auto-progresses an order through assignment → report without a real inspector, so we can demo a complete round-trip end-to-end.

---

## 🔴 PROD readiness (whole PROD picture, none captured yet)

- PROD endpoint URL (sandbox is `https://clients.valorvaluations.com/adapters/Integration/Acuity` — confirm PROD hostname)
- PROD credentials handover process — who, when, how delivered
- PROD MasterClientID, BranchID, SenderID, RecipientID
- PROD inbound URL re-registration process (Valor only supports a single outbound URL slot — what's their change-control? Same-day, ticket, etc.)
- Are PROD test orders allowed before go-live, or strictly real orders only
- Production support contact + escalation path
- SLA / monitoring expectations
- Status page or incident notification channel
- Any difference in PROD message behavior vs sandbox we should know about

---

## 🟡 XML wire format — fields, enums, conventions

- Full AcuityOrder field list **Valor actually wants populated** (vs absolute minimum). We have the XSD; we don't know which optional fields move the needle on Valor's side.
- Accepted enum values for: `PropertyType`, `LoanType`, `LoanPurpose`, `ContactType` — get them in writing so our lookup tables are exact.
- `<ForeignOrderIdentifier>` LPA Key / CaseFile ID — confirm exact `Type` attribute values for both, expected `ID` format/length, and whether Valor cares if both are present.
- `AcuityOrderUpdate` — when do they expect it vs a fresh `AcuityOrder`? Which fields are updateable? Any fields that lock once accepted?
- Custom Valor extensions to public 6.4.0 — anything they send or expect that's NOT in the public XSD package?
- `<SalesPrice>` — required / optional / used? (We may not always have it from JaroDesk.)

---

## 🟡 Inbound message coverage (for the beyond-MVP Case build)

- The 8 milestone messages we received on May 7 — **is that the complete superset Valor emits**, or are there more conditional types we haven't seen yet (e.g., AcuityHold, AcuityCancellation, AcuityOnSite, AcuityReassignment)?
- Canonical state machine — what order do messages fire? Which are guaranteed vs conditional?
- Per message type:
  - `AcuityOrderAcceptance` — guaranteed first reply? Carries Provider order ID?
  - `AcuityAssignment` — does this carry inspector name/ID, scheduled appointment time, ETA?
  - `AcuityDelay` — reason codes? Expected resolution date?
  - `AcuityHold` — different from Delay how? Who clears?
  - `AcuityReport` — confirm base64 PDF is always present on final report; can there be multiple attachments (PDF + photos + addenda); max attachment size; supported MIME types beyond PDF
  - `AcuityCancellation` — reasons, refund implications
- **Can Valor send us a sample XML for every message type they emit?** Best single ask for fixture-building.

---

## 🟡 Inbound security

- Valor posts to us unauthenticated — can they add an HMAC signature header (`X-Acuity-Signature` over body with a shared secret)? SenderID alone is spoofable.
- Can they advertise a stable set of source IPs so we can IP-allowlist on our side?
- If we 5xx and exhaust their ~3 retries, what's the replay / recovery mechanism — manual re-trigger from their side, or do we lose the event?

---

## 🟡 Outbound retry & idempotency

- If we POST and the response is delivered but our network breaks before we read it, what's Valor's de-dupe rule on a re-POST with the same `PartnerReferenceNumber`? (Ties into the duplicate-PRN PROD question above.)
- Recommended retry / backoff for transient 5xx from Valor — any specific guidance.

---

## 🟢 Reference data

- Full error code reference. We have:
  - `0500` — schema validation (top-level `<Error>`)
  - `3003` — client profile cannot be determined (wrapped in `<AcuityAcknowledgement>`)
  - What else do they routinely emit (auth, rate limit, business-rule rejects)? Get the list.
- Error code → response shape map (which codes wrap in `<AcuityAcknowledgement>` vs ride at top level).

---

## 🟢 Operations, billing, sandbox hygiene

- Sandbox usage limits or daily caps?
- PROD billing model — per-order, monthly minimum, tier?
- Are PDR and PDC priced differently despite sharing ProductCode `9`? How is billing line-itemed?
- Cancellation billing — partial fee, full fee, free if cancelled before assignment?
- Rejection billing — does a 3003 / schema reject ever charge?
- Sandbox cleanup of stale test orders (e.g., `1098324.1` from May 4) — automatic or do we ask?

---

## 🟢 Beyond-MVP, Case-building direction

- Tell Valor we're building a Case model that mirrors their state machine in JaroDesk — ask if they have a recommended canonical status taxonomy other clients use that we should align to (saves us inventing one).
- Any of their other client integrations do something interesting on AcuityReport receipt that you'd recommend? (Free intelligence on patterns that work.)

---

## Top two single asks (if time is short)

1. **Send sample XML for every inbound message type Valor emits** — one Postman dump unblocks the whole Case build.
2. **Publish their full error code list** — so our error parser has a complete enum to map against.

---

# Live Meeting Notes — typed during call

## JaroDesk Vendor Profile setup

- **Production vendor email:** `orders@valorvaluations.com`
- **Sandbox / test vendor email:** `jeanette@valorvaluations.com`
- **Provisional plan:** add `jeanette@valorvaluations.com` to the live vendor account to start (use real vendor record, sandbox contact, so test orders flow through real JaroDesk routing without a parallel vendor record).

## Account ID correction

- **MasterClientID `56135` + BranchID `1055` are PRODUCTION values**, not sandbox.
- Earlier `context.md` listed them under "Dev (Sandbox)" — that's wrong; needs to be fixed post-meeting.
- **Sandbox MasterClientID + BranchID are still unknown** — separate ask for Valor if relevant (only matters if the IDs need to be on the wire).

## ✅ XML placement: MasterClientID / BranchID — RESOLVED

- **Confirmed by Valor:** MasterClientID and BranchID do **NOT** need to be on the wire.
- Only the **SenderID = `OPTEONAMC`** is required for identification on outbound.
- Basic Auth + SenderID is the full identity binding. Master / Branch are Valor-side account record fields, not message fields.
- **Implication:** original hypothesis (pre-3003) was correct all along. No XML schema extension needed. Existing AcuityOrder XML (no Master/Branch fields) ships as-is.

## ✅ Duplicate PartnerReferenceNumber in PROD — RESOLVED

- **PROD behavior:** Valor returns **error code `3019`** on duplicate `PartnerReferenceNumber`.
- Every order is expected to be unique — Valor does not silently accept retries.
- Sandbox accepting duplicates was non-representative; PROD is stricter.
- **Our handling responsibility:** when `3019` fires, write a message into JaroDesk (note / case event) to indicate duplicate detection. Surface visibly to the order owner — don't swallow.
- **New error code to add to enum:**
  - `3019` — duplicate PartnerReferenceNumber rejected
  - Confirm shape: top-level `<Error>` vs `<AcuityAcknowledgement><Error>` (matters for the outbound error parser widening — punch-list #4).
- **Retry implication:** outbound retries on transient 5xx must NOT re-send the same `PartnerReferenceNumber`; the network-failure-but-already-delivered race is now a real risk. May need an idempotency table (Dataverse) keyed on PartnerReferenceNumber to track "sent / acked" before retrying.

## ⚠️ Fast-complete sandbox — NOT AVAILABLE

- **Valor confirmed:** they cannot submit test orders to the GSE APIs (Fannie / Freddie) from sandbox.
- They cannot do a test submission to the API (no magic fast-complete code, no scripted auto-progress to AcuityReport).
- **Implication for sandbox testing:**
  - **PDC end-to-end** may still be demoable (no GSE round-trip required) — needs confirmation that a real test inspector can complete a sandbox PDC.
  - **PDR end-to-end is gated** by lack of GSE sandbox — we can validate the wire (XML accepted, AcuityOrderAcceptance, AcuityAssignment) but not the GSE submission step or the full report-back loop.
- **Plan-B options to discuss:**
  - Can Valor manually complete a sandbox order on their side (push an `AcuityReport` to us against a known `PartnerReferenceNumber`) so we get a real round-trip fixture for the inbound flow?
  - Is there a "stub report" sandbox mode where Valor returns a canned PDF?
  - Are the 8 milestone messages from May 7 the complete superset we'll ever receive in sandbox (i.e., they stop short of `AcuityReport`)?

## 🚨 Major framing correction: there is no separate sandbox

- **Both Opteon and Valor are operating in PROD on both sides.** The `https://clients.valorvaluations.com/adapters/Integration/Acuity` endpoint IS the production endpoint — there is no separate "sandbox" environment to graduate to.
- Earlier prep notes assumed a sandbox → PROD promotion step. **That step does not exist.**
- **Implications:**
  - "PROD readiness" section above (PROD endpoint URL, PROD credentials, PROD account IDs) is mostly moot — we already have the PROD values. Existing creds + SenderID `OPTEONAMC` + Valor URL are PROD.
  - PROD MasterClientID `56135` + BranchID `1055` are confirmed PROD values (consistent with this).
  - Pipeline DEV → UAT → PROD on **our** side still applies (Power Automate environment promotion), but each environment talks to the same Valor endpoint with the same creds.
  - "Fast-complete sandbox" limitation = no fast-complete in **any** environment, since there's only one Valor environment.
  - Every test order we send IS a real Valor order. Treat with appropriate caution — possible billing, vendor confusion, real inspector dispatch if not flagged correctly.
- **Open question to confirm:** is there a way to flag a test order so Valor doesn't actually dispatch an inspector (e.g., a specific test ProductCode, or test SenderID, or test address that Valor's system recognizes as non-billable)?

## JaroDesk → AcuityOrder XML field mapping (intel from this call)

| JaroDesk field | Acuity / Valor XML field | Notes |
|----------------|--------------------------|-------|
| Entry contact | `PropertyAccess` | The Entry contact on the JaroDesk order maps to Valor's `PropertyAccess` element. |
| (JaroDesk PropertyType) | `PropertyType` | Passed over as-is — Valor accepts current values. |
| (JaroDesk LoanType) | `LoanType` | Passed over as-is — Valor accepts current values. |
| (JaroDesk LoanPurpose) | `LoanPurpose` | Passed over as-is — Valor accepts current values. |
| (JaroDesk ContactType) | `ContactType` | Passed over as-is — Valor accepts current values. |

**Enum mapping status:** the four enum fields (`PropertyType`, `LoanType`, `LoanPurpose`, `ContactType`) need no transformation layer — JaroDesk values map 1:1 into Valor's expected values. Removes the "get accepted enum values in writing" task from the prep list.

## ✅ ForeignOrderIdentifier — RESOLVED (and corrects context.md)

- **Mutually exclusive** — never both LPA Key and CaseFile ID on the same order.
- The two GSE-program pairings:
  - **Freddie Mac ACE program** → product is **PDR** → carry `ForeignOrderIdentifier Type="FreddieMacLPAKey"`.
  - **Fannie Mae ValueAcceptance program** → product is **PDC** → carry `ForeignOrderIdentifier Type="FannieMaeCaseFileID"`.
- `Type` attribute values are exactly as defined in the public 6.4.0 XSD enum (`FreddieMacLPAKey`, `FannieMaeCaseFileID`).
- **context.md correction needed (post-meeting):** the "PDC = no ID / PDR = ID present" mapping in `context.md` is **wrong**. Both PDR and PDC carry an ID — different GSE identifier types depending on which program drove the order.
- **Routing rule update:** the JaroDesk-side decision becomes "which GSE program is this loan under?" not "is there a GSE ID at all?". ACE → PDR, ValueAcceptance → PDC. Same `ProductCode=9` for both.

## ✅ SalesPrice — NOT USED

- Valor does **not** consume `<SalesPrice>` at all.
- Drop the field from the outbound AcuityOrder XML — saves us a JaroDesk lookup and removes a "may be missing" risk we'd otherwise have to handle.
- Update the JaroDesk → Acuity field mapping table in `context.md` to remove the `SalesPrice` row.

## ✅ JaroDesk source for GSE identifiers — KNOWN (Sal 2026-05-15)

- **Endpoint:** `GET https://api.jarodesk.com/v1/order/{order_id}/incremental`
- **Body path:**
  - `body.details.details.lpaKey` → maps to AcuityOrder `<ForeignOrderIdentifier Type="FreddieMacLPAKey"/>`
  - `body.details.details.duCaseFileId` → maps to AcuityOrder `<ForeignOrderIdentifier Type="FannieMaeCaseFileID"/>`
- **Sample response:**
  ```json
  "details": {
    "order_id": 22022381,
    "type": "alternative",
    "details": {
      "lpaKey": "AN815824",
      "duCaseFileId": "AN815824"
    }
  }
  ```
- **Router-side work needed for v37:**
  - Add `HTTP_-_Get_Order_Incremental` action (router currently only calls `/v1/order/{id}`, not `/incremental`).
  - Parse `lpaKey` and `duCaseFileId` from `body.details.details`.
  - Populate router variables `FreddieMacLPAKey` + `FannieMaeCaseFileID`.
  - Pass to Acuity Outbound child in PDR and PDC cases (child's trigger schema already accepts them as of v36).
- **Note on the sample:** both fields are populated with the same value (`AN815824`). Per Valor 2026-05-14 the two identifiers are mutually exclusive, so the router should still respect the routing case (PDR → use lpaKey, PDC → use duCaseFileId) rather than emitting both when JaroDesk over-populates.

## ✅ Inbound message coverage — DELIVERABLES COMMITTED

- **Valor (Jeanette) will extract** the full list of inbound message types Valor can emit, and send it over. Awaiting follow-up.
- **Sal has the raw XML** for the 8 messages received on May 7, 2026 — these are real Valor-emitted fixtures we can build the Case logic against without waiting for Jeanette's list.
- **Action items post-meeting:**
  1. Save the 8 raw XMLs into `projects/AcuityIntegration/responses/inbound_2026-05-07_*.xml` so they're version-controlled as test fixtures (mirror to local repo + SharePoint).
  2. Read each one to map message type → carried fields → JaroDesk Case write.
  3. When Jeanette's full-type-list arrives, diff against the 8 we have to identify which message types are NOT yet captured (need synthetic fixtures or wait for live emission).

## 🐛 Bug found in `response-report.md` — inbound ack SenderID is wrong

- **Symptom:** in the AcuityAcknowledgement we send back to Valor (line 92 of `responses/response-report.md`), `<SenderID>` is `OPTEON`, but our SenderID is **always** `OPTEONAMC`.
- **Likely cause:** the inbound flow is reading the malformed Dataverse `cre4a_apikey` value (`"OPTEON"`) directly. This is the same root cause as the May 4 latent bug noted in 10-progress.md punch-list #6 (generator expects pipe-delimited `OPTEONAMC|VALOR|9`).
- **Fix scope:**
  - Update Dataverse `cre4a_apikey` to `OPTEONAMC|VALOR|9` (pipe-delimited as the generator expects), OR
  - Refactor the inbound flow to read `OPTEONAMC` from a fixed source (env var or correctly-split apikey field), independent of `cre4a_apikey`.
- **Risk:** if Valor ever tightens validation to enforce SenderID matching across outbound + inbound-ack, every report receipt we ack today is technically inconsistent. Low immediate risk (Valor's accepting it), real risk for PROD strictness.
- Bundle with punch-list #6 (`cre4a_apikey` fix) — same underlying repair.
