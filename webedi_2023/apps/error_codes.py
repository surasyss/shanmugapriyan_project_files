"""
List of error codes being used in Integrator

Please make sure to add entries in an alphabetical order
"""
from spices.enum_utils import BaseChoice


class ErrorCode(BaseChoice):
    ACCOUNT_DISABLED_FAILED_WEB = (
        "intgrt.account_disabled.web",
        "Account is disabled, please check activate the account (username: {username})",
    )
    AUTHENTICATION_FAILED_FTP = (
        "intgrt.auth_failed.ftp",
        "Authentication failed, please check FTP credentials",
    )
    AUTHENTICATION_FAILED_WEB = (
        "intgrt.auth_failed.web",
        "Website login failed, please check login credentials (username: {username})",
    )
    USER_PERMISSION_INVOICE_NOT_ENROLLED = (
        "intgrt.permission.invoice_not_enrolled",
        "Invoices are not available, please check if user is enrolled for e-invoices",
    )
    COMMON_UNSUPPORTED_OPERATION = (
        "intgrt.common.unsupported_operation",
        "This operation is not supported",
    )
    EXTERNAL_UPSTREAM_UNAVAILABLE = (
        "intgrt.external.upstream_unavailable",
        "Could not connect because website was unavailable",
    )
    WEBSITE_UNDER_MAINTENANCE = (
        "intgrt.external.website_under_maintenance",
        "Could not connect because website is under maintenance",
    )
    # Payment Export related
    PE_BANK_ACC_NOT_FOUND = (
        "intgrt.payment_export.bank_account_not_found",
        "Specified bank account '{bank_account}' was not found",
    )
    PE_BANK_ACC_SELECTION_FAILED = (
        "intgrt.payment_export.bank_account_selection_failed",
        "Something went wrong while selecting bank account '{bank_account}'",
    )
    PE_CHECKRUN_ALREADY_EXISTS = (  # Internal exception / issue
        "intgrt.payment_export.checkrun_already_exists",
        "Specified payment '{payment_number}' has already been exported via Plate IQ",
    )
    PE_DUPLICATE_TXN_FOUND = (
        "intgrt.payment_export.duplicate_txn_found",
        "We found another payment that looked similar to this one {prefix_number}, {amount}. "
        "In order to avoid duplicates, we did not export this payment. "
        "Please export manually or contact support.",
    )
    PE_FISCAL_PERIOD_NOT_SET = (
        "intgrt.payment_export.fiscal_period_not_set",
        "Fiscal period not set",
    )
    PE_INSUFFICIENT_PERMISSIONS = (
        "intgrt.payment_export.insufficient_permissions",
        "The provided user {username} might have insufficient permissions",
    )
    PE_INVALID_DISCOVERED_FILE = (
        "intgrt.payment_export.invalid_discovered_file",
        "To download invoices, found invalid discovered file.",
    )
    PE_INVOICE_ALREADY_PAID = (
        "intgrt.payment_export.invoice_already_paid",
        "One or more invoices have already been paid: {invoice_numbers}",
    )
    PE_INVOICE_NOT_APPROVED = (
        "intgrt.payment_export.invoice_not_approved",
        "One or more invoices were not approved: {invoice_numbers}.",
    )
    PE_INVOICE_NOT_FOUND = (
        "intgrt.payment_export.invoice_not_found",
        "One or more invoices were not found: {invoice_numbers}. This can mean that the invoice was not exported "
        "to the accounting system, or it has already been marked as paid manually directly in the accounting system. "
        "If the payment has already been added manually by you or your teammates, you can mark the payment as exported "
        "in Plate IQ.",
    )
    PE_INVOICE_SELECTION_FAILED = (
        "intgrt.payment_export.invoice_selection_failed",
        "Something went wrong while selecting invoices for payment",
    )
    PE_LOCATION_NOT_FOUND = (
        "intgrt.payment_export.location_not_found",
        "Specified location name '{location_name}' was not found",
    )
    PE_LOCATION_SELECTION_FAILED = (
        "intgrt.payment_export.location_selection_failed",
        "Something went wrong while selecting location {location_name}",
    )
    PE_PAYMENT_AMOUNT_NEGATIVE = (
        "intgrt.payment_export.payment_amount_negative",
        "Exports for negative payments are not supported. Please change the payment or export the payment manually.",
    )
    PE_PAYMENT_CONFLICT = (
        "intgrt.payment_export.payment_conflict",
        "Specified payment '{payment_number}' already exists in accounting system",
    )
    PE_VALIDATION_AMOUNT_MISMATCH = (
        "intgrt.payment_export.validation.amount_mismatch",
        "There was a mismatch between the payment amount and selected invoices total",
    )
    PE_VENDOR_NOT_FOUND = (
        "intgrt.payment_export.vendor_not_found",
        "Specified vendor name '{vendor_name}' was not found",
    )
    PE_VENDOR_SELECTION_FAILED = (
        "intgrt.payment_export.vendor_selection_failed",
        "Something went wrong while selecting vendor {vendor_name}",
    )
    PE_RESPONSE_VALIDATION_FAILED = (
        "intgrt.payment_export.response_validation_failed",
        "Payment export failed: {error_message}",
    )
    # payment automate related
    VP_INVOICE_SELECTION_FAILED = (
        "intgrt.vendor_payment.invoice_selection_failed",
        "No invoice with given invoice id found : {invoice_id}",
    )
    VP_INVOICE_AMOUNT_MISMATCHED_FAILED = (
        "intgrt.vendor_payment.invoice_vcard_amount_mismatch",
        "Card limit amount and invoice due amount does not match {invoice_id}",
    )
