from typing import List
from backend.models.semantic import ElectricityBillSemantic
from backend.models.validation import ValidationCheck, ValidationResult


class UrjaValidator:
    def validate(self, semantic: ElectricityBillSemantic) -> ValidationResult:
        checks: List[ValidationCheck] = []
        overall_status = "passed"

        # Check 1: Meter Reading Calculation
        prev = semantic.meter.previous_reading
        curr = semantic.meter.current_reading
        mult = semantic.meter.meter_multiplier or 1.0
        units = semantic.meter.units_consumed

        if prev is not None and curr is not None:
            calc_diff = round((curr - prev) * mult, 2)
            if units is not None:
                if abs(calc_diff - round(units, 2)) <= 0.1:
                    checks.append(ValidationCheck(
                        name="meter_reading_calculation",
                        status="passed",
                        field="meter.units_consumed",
                        message=f"Verified: ({curr} - {prev}) × {mult} = {calc_diff} units consumed.",
                        details={"calculated_units": calc_diff, "reported_units": units}
                    ))
                else:
                    checks.append(ValidationCheck(
                        name="meter_reading_calculation",
                        status="warning",
                        field="meter.units_consumed",
                        message=f"Mismatch: Calculated ({curr} - {prev}) × {mult} = {calc_diff}, but reported units = {units}.",
                        details={"calculated_units": calc_diff, "reported_units": units}
                    ))
                    if overall_status == "passed":
                        overall_status = "passed_with_warnings"

        # Check 2: Bill Amount Addition Sanity (Fixed Arrears vs Current Bill vs Payable)
        curr_amt = semantic.money.current_bill_amount
        arrears = semantic.money.arrears or 0.0
        payable = semantic.money.payable_amount

        if curr_amt is not None and payable is not None:
            calc_total = round(curr_amt + arrears, 2)
            if abs(calc_total - round(payable, 2)) <= 1.0:
                checks.append(ValidationCheck(
                    name="bill_amount_addition",
                    status="passed",
                    field="money.payable_amount",
                    message=f"Verified: Current Bill (₹{curr_amt}) + Arrears (₹{arrears}) = Payable (₹{payable}).",
                    details={"current_bill": curr_amt, "arrears": arrears, "payable": payable}
                ))
            else:
                checks.append(ValidationCheck(
                    name="bill_amount_addition",
                    status="warning",
                    field="money.payable_amount",
                    message=f"Note: Current Bill (₹{curr_amt}) + Arrears (₹{arrears}) = ₹{calc_total}, reported payable = ₹{payable}.",
                    details={"expected": calc_total, "reported": payable}
                ))
                if overall_status == "passed":
                    overall_status = "passed_with_warnings"

        # Check 3: Sanctioned Load
        if semantic.connection.sanctioned_load_kw is not None:
            if semantic.connection.sanctioned_load_kw > 0:
                checks.append(ValidationCheck(
                    name="sanctioned_load_sanity",
                    status="passed",
                    field="connection.sanctioned_load_kw",
                    message=f"Sanctioned load is valid: {semantic.connection.sanctioned_load_kw} kW."
                ))

        # Surface competing evidence without changing any extracted value.
        for field_name, candidates in semantic.candidates.items():
            values = {str(candidate.value) for candidate in candidates}
            if len(values) > 1:
                checks.append(ValidationCheck(name="evidence_conflict", status="conflict", field=field_name, message=f"Conflicting source values: {sorted(values)}", details={"candidates": [candidate.model_dump() for candidate in candidates]}))
                overall_status = "conflict"

        # Check 4: Cross-Page Evidence Corroboration
        acc_ev = [ev for ev in semantic.evidence if ev.field == "account.account_number"]
        if len(acc_ev) > 1:
            vals = set(ev.value for ev in acc_ev)
            if len(vals) == 1:
                checks.append(ValidationCheck(
                    name="cross_page_corroboration",
                    status="passed",
                    field="account.account_number",
                    message=f"Corroborated account number '{next(iter(vals))}' across {len(acc_ev)} occurrences."
                ))
            else:
                checks.append(ValidationCheck(
                    name="cross_page_corroboration",
                    status="conflict",
                    field="account.account_number",
                    message=f"Conflict detected for account number across pages: {list(vals)}."
                ))
                overall_status = "conflict"

        return ValidationResult(status=overall_status, checks=checks)
