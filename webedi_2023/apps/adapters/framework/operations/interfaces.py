from apps.error_codes import ErrorCode
from spices.services import ContextualError


# pylint: disable=no-member,no-self-use
class AbstractVendorConnector:
    """
    What BUSINESS operations does a Vendor connector support? Only add methods here that have business value.
    If the method name has ANYTHING technical in it, it does not belong here.
    """

    def navigate_to_home_page(self):
        """Navigate to home page"""
        raise ContextualError(
            code=ErrorCode.COMMON_UNSUPPORTED_OPERATION.ident,
            message=ErrorCode.COMMON_UNSUPPORTED_OPERATION.message,
            params={"operation": "navigate_to_home_page"},
        )

    def perform_login(self):
        """Navigate to login page, and submit login information"""
        raise ContextualError(
            code=ErrorCode.COMMON_UNSUPPORTED_OPERATION.ident,
            message=ErrorCode.COMMON_UNSUPPORTED_OPERATION.message,
            params={"operation": "perform_login"},
        )

    def download_invoices(self):
        raise ContextualError(
            code=ErrorCode.COMMON_UNSUPPORTED_OPERATION.ident,
            message=ErrorCode.COMMON_UNSUPPORTED_OPERATION.message,
            params={"operation": "download_invoices"},
        )

    def make_payments(self):
        raise ContextualError(
            code=ErrorCode.COMMON_UNSUPPORTED_OPERATION.ident,
            message=ErrorCode.COMMON_UNSUPPORTED_OPERATION.message,
            params={"operation": "make_payments"},
        )


# pylint: enable=no-member
