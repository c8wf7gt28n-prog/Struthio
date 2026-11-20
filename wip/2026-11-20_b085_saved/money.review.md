# money review: DONE (result: b085/money.review.result.json)
- Verdict: accept_after_fixes. 4 must-fix, 10 should-fix.
- Copy: main tree 2a4c172 + money.patch; applies clean; registry matches. Copy deleted; logs/probes in b085/money/review/.
- Tests: 16 modules x 2 looks = 297 per look, 0 failing; tier 0 both looks 52 runs / 870 tests / 0 failing.
- Must: named-date + months/business days refused ('does not use d'); round '0' -> ZeroDivisionError through Kernel.dispatch;
  money/dates tool family too broad (plan 4755->6280 chars for 'open the price list sheet'); '(exact 3.33 USD (exact 10/3 USD))'.
- Mutants: halfup, owners, noclamp, noexcl caught; clamp flag, weekend holiday, precedence guard NOT caught.
