import datetime
from typing import List
from backend.models import UrjaBillSchema, ValidationCheck, ValidationResult


class UrjaValidator:
    def validate(self, schema: UrjaBillSchema) -> UrjaBillSchema:
        checks: List[ValidationCheck] = []
        overall_status = "passed"

        # Check 1: Meter Reading Calculation Consistency
        prev_read = schema.meter.previous_reading
        curr_read = schema.meter.current_reading
        mult = schema.meter.meter_multiplier or 1.0
        units = schema.meter.units_consumed

        if prev_read is not None and curr_read is not None:
            calc_diff = curr_read - prev_read
            calc_units = round(calc_diff * mult, 2)
            
            if units is not None:
                diff = abs(calc_units - units)
                if diff < 0.1:  # small floating point tolerance
                    checks.append(ValidationCheck(
                        name="meter_reading_calculation",
                        status="passed",
                        field="meter.units_consumed",
                        message=f"Verified: ({curr_read} - {prev_read}) × {mult} = {calc_units} units consumed.",
                        details={"calculated_units": calc_units, "reported_units": units}
                    ))
                else:
                    checks.append(ValidationCheck(
                        name="meter_reading_calculation",
                        status="warning",
                        field="meter.units_consumed",
                        message=f"Mismatch: Calculated ({curr_read} - {prev_read}) × {mult} = {calc_units}, but reported units = {units}.",
                        details={"calculated_units": calc_units, "reported_units": units}
                    ))
                    if overall_status == "passed":
                        overall_status = "passed_with_warnings"
            else:
                schema.meter.units_consumed = calc_units
                schema.consumption.current_units = calc_units
                checks.append(ValidationCheck(
                    name="meter_reading_calculation",
                    status="passed",
                    field="meter.units_consumed",
                    message=f"Calculated units from meter readings: ({curr_read} - {prev_read}) × {mult} = {calc_units}.",
                    details={"calculated_units": calc_units}
                ))

        # Check 2: Bill Amount Addition Sanity
        curr_amt = schema.billing.current_bill_amount
        arrears = schema.billing.arrears or 0.0
        payable = schema.billing.payable_amount

        if curr_amt is not None and payable is not None:
            expected_total = round(curr_amt + arrears, 2)
            if abs(expected_total - round(payable, 2)) <= 1.0:  # Allow 1 rupee rounding
                checks.append(ValidationCheck(
                    name="bill_amount_addition",
                    status="passed",
                    field="billing.payable_amount",
                    message=f"Verified: Current Bill (₹{curr_amt}) + Arrears (₹{arrears}) = Payable (₹{payable}).",
                    details={"current_bill": curr_amt, "arrears": arrears, "payable": payable}
                ))
            else:
                checks.append(ValidationCheck(
                    name="bill_amount_addition",
                    status="warning",
                    field="billing.payable_amount",
                    message=f"Note: Current Bill (₹{curr_amt}) + Arrears (₹{arrears}) = ₹{expected_total}, reported payable = ₹{payable}.",
                    details={"expected": expected_total, "reported": payable}
                ))
                if overall_status == "passed":
                    overall_status = "passed_with_warnings"

        # Check 3: Numeric Sanity Checks
        if schema.connection.sanctioned_load_kw is not None:
            if schema.connection.sanctioned_load_kw > 0:
                checks.append(ValidationCheck(
                    name="sanctioned_load_sanity",
                    status="passed",
                    field="connection.sanctioned_load_kw",
                    message=f"Sanctioned load is valid: {schema.connection.sanctioned_load_kw} kW."
                ))
            else:
                checks.append(ValidationCheck(
                    name="sanctioned_load_sanity",
                    status="warning",
                    field="connection.sanctioned_load_kw",
                    message=f"Sanctioned load value is zero or negative."
                ))

        # Check 4: Cross-page evidence corroboration
        acc_ev = [ev for ev in schema.evidence if ev.field == "bill.account_number"]
        if len(acc_ev) > 1:
            values = set(ev.value for ev in acc_ev)
            if len(values) == 1:
                checks.append(ValidationCheck(
                    name="cross_page_corroboration",
                    status="passed",
                    field="bill.account_number",
                    message=f"Corroborated account number '{next(iter(values))}' across {len(acc_ev)} occurrences."
                ))
            else:
                checks.append(ValidationCheck(
                    name="cross_page_corroboration",
                    status="conflict",
                    field="bill.account_number",
                    message=f"Conflict detected for account number across pages: {list(values)}."
                ))
                overall_status = "conflict"

        schema.validation = ValidationResult(
            status=overall_status,
            checks=checks
        )
        return schema
