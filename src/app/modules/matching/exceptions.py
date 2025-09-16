# src/app/modules/matching/exceptions.py


class MatchException(Exception):
    """Base exception for all 3-way matching errors."""

    def __init__(self, message: str, details: dict = None):
        super().__init__(message)
        self.details = details if details is not None else {}

    def to_dict(self):
        return {
            "type": self.__class__.__name__,
            "message": str(self),
            **self.details,
        }


# --- Document-Level Exceptions ---
class MissingDocumentException(MatchException):
    """Raised when a related document (PO, GRN) cannot be found."""

    pass


class DuplicateInvoiceException(MatchException):
    """Raised when an invoice with the same ID for the same vendor is detected."""

    pass


class TimingMismatchException(MatchException):
    """Raised when document dates are not in a logical sequence."""

    pass


# --- Item-Level Exceptions ---
class ItemMismatchException(MatchException):
    """Raised when an item on an invoice is not found on the PO or GRN."""

    pass


class QuantityMismatchException(MatchException):
    """Raised when quantities do not align between documents."""

    pass


class PriceMismatchException(MatchException):
    """Raised when the unit price on the invoice differs from the PO, beyond tolerance."""

    pass


class OverBillingException(MatchException):
    """Raised when the cumulative billed/received quantity exceeds the PO quantity."""

    pass


# --- Financial Calculation Exceptions ---
class FinancialMismatchException(MatchException):
    """Raised when line totals or grand totals are calculated incorrectly on the invoice."""

    pass
