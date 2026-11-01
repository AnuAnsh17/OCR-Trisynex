from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class EvidenceItem(BaseModel):
    field: str
    value: Any
    page: int
    source_table: Optional[str] = None
    source_text: str
    confidence: Optional[float] = None
    bbox: Optional[List[float]] = None


class ProviderInfo(BaseModel):
    name: Optional[str] = None
    short_name: Optional[str] = None
    state: Optional[str] = None
    circle: Optional[str] = None
    division: Optional[str] = None
    subdivision: Optional[str] = None
    office: Optional[str] = None
    website: Optional[str] = None
    customer_portal: Optional[str] = None
    gstin: Optional[str] = None
    cin: Optional[str] = None


class CustomerInfo(BaseModel):
    name: Optional[str] = None
    name_local: Optional[str] = None
    father_husband_name: Optional[str] = None
    address: Optional[str] = None
    address_local: Optional[str] = None
    mobile: Optional[str] = None
    email: Optional[str] = None


class AccountInfo(BaseModel):
    account_number: Optional[str] = None
    consumer_number: Optional[str] = None
    customer_id: Optional[str] = None
    bill_number: Optional[str] = None


class BillInfo(BaseModel):
    bill_type: Optional[str] = None
    bill_month: Optional[str] = None
    bill_date: Optional[str] = None
    printed_date: Optional[str] = None
    billing_period_start: Optional[str] = None
    billing_period_end: Optional[str] = None
    due_date: Optional[str] = None
    disconnection_date: Optional[str] = None
    bill_basis: Optional[str] = None
    currency: str = "INR"


class ConnectionInfo(BaseModel):
    connection_type: Optional[str] = None
    connection_date: Optional[str] = None
    supply_type: Optional[str] = None
    category: Optional[str] = None
    tariff_code: Optional[str] = None
    tariff_description: Optional[str] = None
    sanctioned_load_kw: Optional[float] = None
    billed_demand_kw: Optional[float] = None
    phase: Optional[str] = None
    voltage: Optional[str] = None
    billing_unit: Optional[str] = None
    division: Optional[str] = None
    subdivision: Optional[str] = None
    feeder: Optional[str] = None
    pole_number: Optional[str] = None
    dtc_number: Optional[str] = None
    e_kyc: Optional[str] = None
    metering_arrangement: Optional[str] = None


class MeterInfo(BaseModel):
    meter_number: Optional[str] = None
    meter_type: Optional[str] = None
    meter_status: Optional[str] = None
    previous_reading: Optional[float] = None
    current_reading: Optional[float] = None
    previous_reading_date: Optional[str] = None
    current_reading_date: Optional[str] = None
    reading_difference: Optional[float] = None
    meter_multiplier: Optional[float] = None
    units_consumed: Optional[float] = None
    reading_remark: Optional[str] = None


class BillMoney(BaseModel):
    previous_dues: Optional[float] = None
    arrears: Optional[float] = None
    current_bill_amount: Optional[float] = None
    net_bill_amount: Optional[float] = None
    payable_amount: Optional[float] = None
    minimum_payable_amount: Optional[float] = None
    due_date_rebate: Optional[float] = None
    payable_by_due_date: Optional[float] = None
    post_due_amount: Optional[float] = None
    late_payment_surcharge: Optional[float] = None
    security_deposit: Optional[float] = None


class ChargeItem(BaseModel):
    charge_id: str
    label: str
    label_local: Optional[str] = None
    amount: Optional[float] = None
    category: str = "other"  # energy, demand, duty, fppa, lpsc, tax, rebate, subsidy, penalty, other
    source_table: Optional[str] = None


class TariffSlab(BaseModel):
    slab_range: Optional[str] = None
    units: Optional[float] = None
    rate: Optional[float] = None
    gross_amount: Optional[float] = None
    cross_subsidy: Optional[float] = None
    govt_subsidy: Optional[float] = None
    net_payable: Optional[float] = None


class ConsumptionHistoryItem(BaseModel):
    period: Optional[str] = None
    units: Optional[float] = None
    demand_kw: Optional[float] = None


class SolarNetMetering(BaseModel):
    assessed_units: Optional[float] = None
    opening_surplus_units: Optional[float] = None
    closing_surplus_units: Optional[float] = None
    p2p_sold_units: Optional[float] = None
    p2p_bought_units: Optional[float] = None


class PaymentDetails(BaseModel):
    last_payment_date: Optional[str] = None
    last_payment_amount: Optional[float] = None
    last_payment_mode: Optional[str] = None
    last_receipt_number: Optional[str] = None
    payment_channels: List[str] = Field(default_factory=list)


class SecurityDepositInfo(BaseModel):
    amount: Optional[float] = None
    type: Optional[str] = None
    due_date: Optional[str] = None


class ElectricityBillSemantic(BaseModel):
    domain: str = "electricity_bill"
    provider: ProviderInfo = Field(default_factory=ProviderInfo)
    customer: CustomerInfo = Field(default_factory=CustomerInfo)
    account: AccountInfo = Field(default_factory=AccountInfo)
    bill: BillInfo = Field(default_factory=BillInfo)
    connection: ConnectionInfo = Field(default_factory=ConnectionInfo)
    meter: MeterInfo = Field(default_factory=MeterInfo)
    money: BillMoney = Field(default_factory=BillMoney)
    charges: List[ChargeItem] = Field(default_factory=list)
    tariff_slabs: List[TariffSlab] = Field(default_factory=list)
    consumption_history: List[ConsumptionHistoryItem] = Field(default_factory=list)
    solar_net_metering: SolarNetMetering = Field(default_factory=SolarNetMetering)
    payment: PaymentDetails = Field(default_factory=PaymentDetails)
    security_deposit: SecurityDepositInfo = Field(default_factory=SecurityDepositInfo)
    provider_specific_fields: Dict[str, Any] = Field(default_factory=dict)
    evidence: List[EvidenceItem] = Field(default_factory=list)
    candidates: Dict[str, List[EvidenceItem]] = Field(default_factory=dict)
