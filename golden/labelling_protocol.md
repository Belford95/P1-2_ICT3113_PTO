# Labelling Protocol (v1.0)

## Section 1: Protocol and Categories

### 1.1 Purpose

The golden set is the reference against which classification accuracy is measured. To keep it trustworthy, every label must come from the ticket text alone and be assigned independently by at least two annotators.

### 1.2 Procedure

1. **Label independently.** Each annotator labels every ticket alone. Do not confer or compare labels until everyone has finished. Labelling should identify 1. The row number of the reviewed ticket, 2. The classified source_label, 3. The original narrative and 4. The confidence rating (see point 4) and lastly, 5. The notes/remarks (for any rating below 3).
2. **Use the ticket text only.** Ignore any category the consumer originally chose for the complaint, because it is unreliable. Do not research the complaint outside the text.
3. **Pick exactly one label.** Read the whole narrative, then choose one of the 7 categories in 1.3, or `None / Unclear` for tickets that fit none (Section 2).
4. **Rate how sure you are of your chosen label.** This is your certainty that the label is the correct category. It is *not* whether the ticket is genuine, serious or valid; every ticket gets labelled, whatever its merit.
   - **3 = Certain:** only one category fits.
   - **2 = Fairly sure:** one category fits best, but another is possible.
   - **1 = Unsure:** two or more categories fit about equally, and you picked the best.
5. **Explain any rating below 3.** In the notes, write one line naming the other category you considered and why you chose yours.
6. **Resolve disagreements.** When all annotators have finished, compare labels. For every ticket where labels differ, discuss it, agree on a final label using the rules in Section 2, and record the final label and the reason. If the disagreement shows a rule is missing or unclear, amend Section 2 and add an entry to the revisions log.
7. **Handle `None / Unclear` tickets.** If every annotator chose `None / Unclear`, exclude the ticket from accuracy scoring, because a classifier limited to the seven categories cannot be scored on it. Record and report the exclusion; do not silently drop it. If annotators differ, resolve it as in step 6, either to one of the seven categories or to an exclusion, with the reason recorded.

### 1.3 Categories

Choose the category for **the financial product or service the consumer's main problem is about**, not the company's name.

| Category | Choose it when the complaint is about... | Don't confuse with |
|---|---|---|
| **Credit reporting** | What appears on a credit report or with the credit bureaus: inaccurate or outdated items, disputes, requests to delete or investigate, identity-theft items on a report, credit-repair services, unauthorised credit inquiries | Debt collection (a collector's behaviour) |
| **Debt collection** | Someone trying to collect money owed: collector calls or letters, requests to validate a debt, "this isn't my debt", old or already-settled debts, harassment, being sued over a debt | The original loan, card or account (its terms or servicing) |
| **Mortgage** | A home loan: applying, refinancing, servicing, escrow, payments, modification, forbearance, foreclosure. Home-equity loans and HELOCs count as mortgages | Auto, student and personal loans |
| **Credit card** | A credit or store card: charges, interest, fees, billing disputes, credit-limit changes, rewards. Prepaid and gift cards go here as the nearest fit | Payment apps and wallets |
| **Bank account or service** | A deposit account at a bank or credit union: checking, savings, CDs, debit cards, ATMs, overdrafts, holds, opening or closing an account | Payment apps, wires, remittances |
| **Consumer loan** | A non-mortgage loan: auto loan or lease, payday, title, personal, instalment or student loan. Covers applying, denial, terms, servicing, fees and refunds | Collection activity on those loans |
| **Money transfer or service** | Moving or holding money outside a bank account: wires, remittances, money orders, payment apps and wallets (e.g. PayPal, Cash App, Venmo), virtual currency. Covers fraud, frozen or closed accounts, failed or unauthorised transfers | Ordinary bank deposit accounts |

## Section 2: Rules for Edge Cases

### 2.1 Tickets that fit two or more categories

Every ticket gets one label. This covers a single problem that fits two categories, and a ticket that mixes several separate complaints. Work through these questions in order and stop at the first that gives an answer:

1. **What does the consumer want done?** Choose the category that handles that request (e.g. "fix my report" → Credit reporting, "stop the calls" → Debt collection). If the ticket contains several separate complaints, the one the consumer most wants resolved is the one to label.
2. **If that doesn't decide it, who is the complaint against?** A credit bureau points to Credit reporting, a collector to Debt collection, a payment app to Money transfer, and so on.
3. **If it is still tied, which issue does the ticket mention first?** Choose that one and rate your certainty 1.

**Judge by facts, not the consumer's wording.** Consumers use words loosely (a card called a "loan", a payment app called a "bank", a lender called a "collector"). Go by how the money moves, who is asking for payment, and what the account is held with.

**Common pairs.** Use these shortcuts before the three questions.

| If the ticket mixes... | Then choose... |
|---|---|
| Credit reporting and Debt collection | **Credit reporting** if the consumer wants the *report* corrected or items removed, even when a collector caused the entry. **Debt collection** if the consumer wants proof of the debt, wants the collector to stop, or is being sued, even when the letter cites credit-report law. |
| Debt collection and the original product (loan, card, mortgage) | **The product** if the complaint is about terms, fees, denial, billing or servicing. **Debt collection** once collectors, collection letters or lawsuits are involved. |
| Credit reporting and a product (card, bank, loan) | **Credit reporting** if the ask is to correct what is reported, even when a bank or card issuer supplied the data. |
| A denied application blamed on the credit report | **Credit reporting** if the consumer disputes the *data* the lender used. The category of the *product applied for* if they dispute the refusal itself. |
| Identity theft | **Credit reporting** if the consumer wants fraudulent items removed from their report. **Debt collection** if a collector is chasing a fraudulent debt. Otherwise the product the fraud happened on. |
| Bank account and Money transfer | **Bank account** for a deposit account at a bank or credit union. **Money transfer** for a payment app, wallet, wire, remittance or crypto exchange. |
| Debit card and prepaid card | **Bank account** for a debit card tied to a checking or savings account. **Credit card** for a reloadable prepaid, gift or benefits card (nearest fit). |
| Credit card and a payment app | A card carrying a payment app's brand is a **Credit card**. The app's balance or account restrictions are **Money transfer**. If both appear, label whichever the consumer most wants resolved. |
| Mortgage and Consumer loan | **Mortgage** if the loan is secured on a home (including HELOCs). Otherwise **Consumer loan**. |
| Fraud or scam (no category of its own) | Label the **product the money passed through** or the loan involved. A hacked payment app is Money transfer, a stolen debit card is Bank account, and a loan-consolidation scam is Consumer loan. |

### 2.2 Tickets that fit none

Use `None / Unclear` only when **both** are true:

- No product in the category table can be identified, or the text is unusable (mostly redaction, a bare legal citation, a fragment).
- You cannot name a best category, even at certainty 1.

More cases that fall here:

- **A product outside the seven categories** (e.g. insurance or investments).
- **A service complaint with no product**, such as rudeness, hold times or unreachable staff. If the context makes the product clear ("no one answers the credit card hotline"), label that product instead.
- **A company named but no product described.** Do not label from the company name alone.

**Hard is not the same as none.** If you can rank a best category, use it and rate 1 or 2. Otherwise the hardest tickets drop out and accuracy looks better than it is.

### 2.3 Ambiguous narratives

| Situation | What to do |
|---|---|
| Very short narrative | Label from what is there. A product word alone is enough (e.g. "I applied for a payday loan and was hung up on" → Consumer loan). |
| Legal or template boilerplate | Ignore the boilerplate. Label from the specific facts and what the consumer asks for. |
| Heavy redaction (`XXXX`, `XX/XX/XXXX`) | Treat redacted text as missing. Do not guess what it hid. |
| Story spans several stages (loan, default, collection, report entry) | Label the stage the consumer's **request** is aimed at, not the earliest event. A debt sold to a collector becomes Debt collection from the sale onward. A mortgage transferred to a new servicer stays Mortgage. |
| Account belongs to someone else (relative, executor, co-signer, joint holder) | Label the **product**. Who owns the account doesn't change the category. |
| Complaint seems weak, untrue or badly written | Label it anyway. Certainty is about your label, not the complaint's merit. Do not skip it or pick a category to balance your labels. |
| Complains about one product but names another's service | Label the product the *problem* is about. |

### 2.4 Revisions log

| Version | Date | Trigger | Change |
|---|---|---|---|
| v1.0 | 2026-09-29 | Initial draft, before any labelling | Categories, edge-case rules, `None / Unclear` policy |
| v2.0 | 2026-09-30 | Unclear on labelling columns        | Updated step 1 of the procedure for clarity          |
| v2.1 | 2026-10-01 | Unclear distinction between Consumer loan and Mortgage | Clarified that a generic loan is Consumer loan unless the ticket states it is secured by a home |

*(For each amendment, add a row: the disagreement that exposed the gap, what changed, and the date.)*
