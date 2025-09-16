#!/usr/bin/env python3
"""
Centralized Logging Configuration for Supervity AP Manager

This module provides a consistent logging setup across the entire application
with proper formatting, levels, and structured output.
"""

import logging
import sys
from typing import Dict, Any, Optional, List
from datetime import datetime
import json
import traceback
from pathlib import Path


# ANSI color codes for console output
class LogColors:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"

    # Foreground colors
    BLACK = "\033[30m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"

    # Background colors
    BG_RED = "\033[41m"
    BG_GREEN = "\033[42m"
    BG_YELLOW = "\033[43m"


class SupervityFormatter(logging.Formatter):
    """Custom formatter with colors and consistent structure"""

    def __init__(self, use_colors: bool = True):
        super().__init__()
        self.use_colors = use_colors

        # Log level to color mapping
        self.level_colors = {
            "DEBUG": LogColors.CYAN,
            "INFO": LogColors.GREEN,
            "WARNING": LogColors.YELLOW,
            "ERROR": LogColors.RED,
            "CRITICAL": LogColors.BG_RED + LogColors.WHITE,
        }

    def format(self, record: logging.LogRecord) -> str:
        # Create timestamp
        timestamp = datetime.fromtimestamp(record.created).strftime("%Y-%m-%d %H:%M:%S")

        # Get color for log level
        level_color = (
            self.level_colors.get(record.levelname, LogColors.WHITE)
            if self.use_colors
            else ""
        )
        reset = LogColors.RESET if self.use_colors else ""

        # Format module path (shorter for readability)
        module_path = record.name
        if module_path.startswith("app."):
            module_path = module_path[4:]  # Remove 'app.' prefix

        # Build the log message
        formatted_msg = f"{LogColors.DIM if self.use_colors else ''}{timestamp}{reset} "
        formatted_msg += f"{level_color}[{record.levelname:8}]{reset} "
        formatted_msg += (
            f"{LogColors.BLUE if self.use_colors else ''}{module_path:25}{reset} "
        )
        formatted_msg += f"| {record.getMessage()}"

        # Add exception info if present
        if record.exc_info:
            formatted_msg += f"\n{self.formatException(record.exc_info)}"

        return formatted_msg


def setup_logging(
    level: str = "INFO", log_file: Optional[str] = None, console_colors: bool = True
) -> None:
    """
    Setup application-wide logging configuration

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional file path to write logs to
        console_colors: Whether to use colors in console output
    """

    # Convert string level to logging constant
    numeric_level = getattr(logging, level.upper(), logging.INFO)

    # Create root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)

    # Clear any existing handlers
    root_logger.handlers.clear()

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(numeric_level)
    console_handler.setFormatter(SupervityFormatter(use_colors=console_colors))
    root_logger.addHandler(console_handler)

    # File handler (if specified)
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(numeric_level)
        file_handler.setFormatter(SupervityFormatter(use_colors=False))
        root_logger.addHandler(file_handler)

    # Suppress noisy third-party loggers
    logging.getLogger("sqlalchemy").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)

    # Log the setup
    logger = logging.getLogger(__name__)
    logger.info(f"Logging initialized - Level: {level}, File: {log_file or 'None'}")


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance for a specific module"""
    return logging.getLogger(name)


def log_extraction_summary(
    logger: logging.Logger,
    file_name: str,
    extraction_data: Dict[str, Any],
    processing_time: Optional[float] = None,
) -> None:
    """
    Log document extraction results in a clean, structured format

    Args:
        logger: Logger instance
        file_name: Name of the processed file
        extraction_data: Extracted data dictionary
        processing_time: Time taken to process (in seconds)
    """

    # Determine document type
    doc_type = extraction_data.get("document_type", "Unknown")

    # Extract key information based on document type
    if doc_type == "Invoice":
        key_fields = {
            "ID": extraction_data.get("invoice_id", "N/A"),
            "Vendor": extraction_data.get("vendor_name", "N/A"),
            "Total": extraction_data.get("grand_total", "N/A"),
            "Date": extraction_data.get("invoice_date", "N/A"),
        }
    elif doc_type == "PurchaseOrder":
        key_fields = {
            "PO#": extraction_data.get("po_number", "N/A"),
            "Vendor": extraction_data.get("vendor_name", "N/A"),
            "Total": extraction_data.get("grand_total", "N/A"),
            "Date": extraction_data.get("order_date", "N/A"),
        }
    elif doc_type == "GoodsReceiptNote":
        key_fields = {
            "GRN#": extraction_data.get("grn_number", "N/A"),
            "PO#": extraction_data.get("po_number", "N/A"),
            "Date": extraction_data.get("received_date", "N/A"),
            "Items": len(extraction_data.get("line_items", [])),
        }
    else:
        key_fields = {"Type": doc_type}

    # Build summary message
    field_str = " | ".join([f"{k}: {v}" for k, v in key_fields.items()])
    time_str = f" | Processing: {processing_time:.2f}s" if processing_time else ""

    logger.info(f"📄 Extracted {doc_type} from '{file_name}' | {field_str}{time_str}")


def log_ingestion_batch_summary(
    logger: logging.Logger,
    job_id: int,
    invoice_count: int,
    po_count: int,
    grn_count: int,
    error_count: int,
    processing_time: Optional[float] = None,
) -> None:
    """Log a summary of batch ingestion results"""

    total_docs = invoice_count + po_count + grn_count
    success_rate = (
        (total_docs / (total_docs + error_count) * 100)
        if (total_docs + error_count) > 0
        else 0
    )

    time_str = f" | Time: {processing_time:.1f}s" if processing_time else ""

    logger.info(
        f"📊 Batch Job {job_id} Complete | "
        f"Invoices: {invoice_count} | POs: {po_count} | GRNs: {grn_count} | "
        f"Errors: {error_count} | Success Rate: {success_rate:.1f}%{time_str}"
    )


def log_matching_result(
    logger: logging.Logger,
    invoice_id: str,
    final_status: str,
    po_matches: int = 0,
    grn_matches: int = 0,
    exceptions: Optional[List[str]] = None,
) -> None:
    """Log invoice matching results in a structured format"""

    status_emoji = {
        "matched": "✅",
        "needs_review": "⚠️",
        "on_hold": "⏸️",
        "rejected": "❌",
    }.get(final_status.lower(), "❓")

    match_str = f"PO: {po_matches}, GRN: {grn_matches}"
    exception_str = f" | Exceptions: {len(exceptions)}" if exceptions else ""

    logger.info(
        f"{status_emoji} Invoice {invoice_id} matching complete | "
        f"Status: {final_status} | Matches: {match_str}{exception_str}"
    )


def log_performance_metric(
    logger: logging.Logger,
    operation: str,
    duration: float,
    items_processed: Optional[int] = None,
    success_count: Optional[int] = None,
) -> None:
    """Log performance metrics for operations"""

    rate_str = ""
    if items_processed and duration > 0:
        rate = items_processed / duration
        rate_str = f" | Rate: {rate:.1f} items/s"

    success_str = ""
    if success_count is not None and items_processed:
        success_rate = (success_count / items_processed) * 100
        success_str = f" | Success: {success_rate:.1f}%"

    logger.info(f"⚡ {operation} | Duration: {duration:.2f}s{rate_str}{success_str}")


def log_error_with_context(
    logger: logging.Logger,
    error: Exception,
    context: Dict[str, Any],
    operation: str = "Operation",
) -> None:
    """Log errors with additional context information"""

    context_str = " | ".join([f"{k}: {v}" for k, v in context.items()])

    logger.error(
        f"❌ {operation} failed | {context_str} | Error: {str(error)}", exc_info=True
    )


# Convenience function for getting module-specific loggers
def get_module_logger(module_file: str) -> logging.Logger:
    """Get a logger named after the calling module"""
    # Extract module name from __file__
    module_name = Path(module_file).stem
    return get_logger(f"app.{module_name}")
