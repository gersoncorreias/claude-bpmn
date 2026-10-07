# Customer Refund — mapping notes

**Source:** `refund-mapping-session.vtt` (mapping session, 3 participants + facilitator, 2m50s)
**Diagram:** [`customer-refund.bpmn`](customer-refund.bpmn) — 7 tasks/events in 3 lanes, validator: 0 findings
**Status:** draft for owner review. Nothing below is confirmed until the process owner signs off.

## Lanes

| Lane | Spoken for by |
|---|---|
| Support Agent | Priya |
| Support Lead | Marco |
| Finance | Dana |

## Steps and evidence

| Step (diagram) | Lane | Evidence |
|---|---|---|
| Refund requested (start) | Support Agent | 00:00:13 Priya: "it starts when a refund request comes in. Most of them are email, some come through chat." |
| Check order against refund policy | Support Agent | 00:00:22 Priya: "open the order and check it against the refund policy" |
| Within policy? → No: Explain decision to customer → Refund declined | Support Agent | 00:00:42 Priya: "I write back and explain why we can't refund it … closed as declined" |
| Over approval limit? | Support Agent | 00:00:53 Priya: "Anything over two hundred dollars I can't approve myself, it goes to Marco" |
| Review refund request | Support Lead | 00:01:25 Marco: "I review it, look at the customer history, and approve it" |
| Approved by lead? → No: Rejected by lead (next step open) | Support Lead | 00:01:45 Marco: "I'd probably talk to the customer myself, or push it back to Priya … we don't have a rule for it" |
| Next refund run (Tue / Fri) | Finance | 00:01:57 Dana: "We run refunds in a batch, Tuesdays and Fridays" |
| Issue refund to original payment method | Finance | 00:02:09 Dana: "we issue the refund to the original payment method" |
| Confirm refund to customer → Refund completed | Support Agent | 00:02:17 Priya: "I send the customer a confirmation … close the ticket as completed" |

## Inferred, not said

- The merge before the refund run: Dana said approved refunds "by Priya or by Marco" both reach Finance (00:01:57), so both paths join there.
- Refunds within policy and under the limit go straight to Finance with no further approval. Nobody described an extra step, but nobody ruled one out.

## Contradictions

- **Approval limit.** Priya says refunds over **$200** go to the lead (00:00:53). Marco says the limit is **$250** since the spring (00:01:06). The diagram uses "Over approval limit?" without a figure. Priya's remark suggests the night shift still applies $200.

## Open questions for the process owner

1. What happens when the Support Lead does not approve a refund? Talk to the customer, return it to the agent, or decline it? (00:01:45). The diagram ends this path at "Rejected by lead (next step open)".
2. Which approval limit is correct, $200 or $250, and how do all shifts learn about a change?
3. Is anything checked between issuing a refund and confirming it to the customer? Today a failed refund is only found at month-end reconciliation (00:02:36). This is outside the diagram for now.
4. Does a chat request follow the same path as an email request? Assumed yes (00:00:13).

## Not modelled

- Month-end reconciliation (00:02:36): mentioned as a safety net, not part of the refund flow.
