
# OneHR Demo — MP05 Foundation Dataset Contract

## Canonical ownership

- Legal company: selected existing `res.company`.
- Operational branch: `onehr.branch`.
- Organization hierarchy: native `hr.department` extended by `onehr_base`.

No parallel company or department model is created.

## Profile shapes

| Profile | Branches | Organization Units | Active MP05 References |
|---|---:|---:|---:|
| QUICK | 2 | 6 | 9 |
| STANDARD | 4 | 10 | 15 |
| FULL ENTERPRISE | 6 | 16 | 23 |

The reference count includes one selected legal-company reference.

## Branch hierarchy

QUICK creates a Jakarta head office plus Bali operational branch. STANDARD adds
Bandung and Surabaya. FULL adds Medan and Makassar. All non-head-office branches
are children of the deterministic Jakarta head office.

## Organization hierarchy

QUICK creates Corporate Services, Human Resources, Finance & Accounting, Operations,
Operations Delivery, and Technology. STANDARD adds Information Technology,
Commercial, Sales, and Marketing. FULL adds Procurement, Learning & Development,
Talent & Succession, Data & Analytics, Customer Experience, and Internal Audit.

## Business time

`valid_from` / `onehr_valid_from` is exactly 730 days before the scenario
`reference_date`; end dates remain open. The generator never uses current date as
business truth. Real execution timestamps remain observability metadata only.

## Identity / adoption

Every generated object has a stable provenance key and a deterministic business code.
If provenance already exists, the target ID must still exist and match. If provenance
does not exist but the exact deterministic business code already exists, it may be
reused only when its company, hierarchy, name, effective dates and business semantics
match the frozen contract. Ambiguity or drift is a hard failure; records are not
silently remapped or rewritten.

