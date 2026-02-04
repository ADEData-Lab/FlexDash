"""
Audit Trail Module for FlexDash.

Logs all data transformations and disclosure decisions
for regulatory compliance and quality assurance.
"""

import logging
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)


@dataclass
class AuditEntry:
    """Single audit log entry."""
    timestamp: str
    operation: str
    component: str
    details: Dict[str, Any]
    user: str = "system"
    success: bool = True
    error_message: Optional[str] = None


class AuditLogger:
    """
    Maintains audit trail of all data operations.

    Logs to both file and memory for runtime access.
    """

    def __init__(self, log_path: Path = None):
        """
        Initialize audit logger.

        Args:
            log_path: Path to audit log file (JSONL format)
        """
        self.log_path = Path(log_path) if log_path else None
        self.entries: List[AuditEntry] = []

        if self.log_path:
            self.log_path.parent.mkdir(parents=True, exist_ok=True)

    def log(
        self,
        operation: str,
        component: str,
        details: Dict[str, Any],
        success: bool = True,
        error_message: str = None
    ) -> AuditEntry:
        """
        Log an operation.

        Args:
            operation: Type of operation (e.g., 'parse', 'validate', 'disclose')
            component: Component performing the operation
            details: Operation-specific details
            success: Whether operation succeeded
            error_message: Error message if failed

        Returns:
            The created AuditEntry
        """
        entry = AuditEntry(
            timestamp=datetime.utcnow().isoformat(),
            operation=operation,
            component=component,
            details=details,
            success=success,
            error_message=error_message
        )

        self.entries.append(entry)

        # Write to file if configured
        if self.log_path:
            with open(self.log_path, 'a') as f:
                f.write(json.dumps(asdict(entry)) + '\n')

        level = logging.INFO if success else logging.ERROR
        logger.log(level, f"AUDIT: {operation} in {component} - {'OK' if success else 'FAILED'}")

        return entry

    def log_ingestion(
        self,
        filename: str,
        records_parsed: int,
        validation_result: Dict = None
    ):
        """Log a data ingestion operation."""
        self.log(
            operation='ingestion',
            component='template_parser',
            details={
                'filename': filename,
                'records_parsed': records_parsed,
                'validation': validation_result or {}
            }
        )

    def log_disclosure_check(
        self,
        dimension: str,
        cell_count: int,
        safe_count: int,
        suppressed_count: int,
        illustrative_count: int
    ):
        """Log disclosure control results."""
        self.log(
            operation='disclosure_control',
            component='disclosure_controller',
            details={
                'dimension': dimension,
                'total_cells': cell_count,
                'safe_cells': safe_count,
                'suppressed_cells': suppressed_count,
                'illustrative_cells': illustrative_count,
                'safety_rate': safe_count / cell_count if cell_count > 0 else 0
            }
        )

    def log_anonymisation(
        self,
        contributors_anonymised: int,
        columns_removed: List[str],
        illustrative_values_generated: int
    ):
        """Log anonymisation operation."""
        self.log(
            operation='anonymisation',
            component='anonymiser',
            details={
                'contributors_anonymised': contributors_anonymised,
                'columns_removed': columns_removed,
                'illustrative_values': illustrative_values_generated
            }
        )

    def log_export(
        self,
        output_type: str,
        filename: str,
        records_exported: int
    ):
        """Log data export operation."""
        self.log(
            operation='export',
            component='exporter',
            details={
                'output_type': output_type,
                'filename': filename,
                'records_exported': records_exported
            }
        )

    def get_summary(self) -> Dict:
        """Get summary of audit log."""
        operations = {}
        for entry in self.entries:
            op = entry.operation
            if op not in operations:
                operations[op] = {'count': 0, 'success': 0, 'failed': 0}
            operations[op]['count'] += 1
            if entry.success:
                operations[op]['success'] += 1
            else:
                operations[op]['failed'] += 1

        return {
            'total_entries': len(self.entries),
            'operations': operations,
            'first_entry': self.entries[0].timestamp if self.entries else None,
            'last_entry': self.entries[-1].timestamp if self.entries else None
        }

    def export_log(self, output_path: Path):
        """Export full audit log to file."""
        with open(output_path, 'w') as f:
            for entry in self.entries:
                f.write(json.dumps(asdict(entry)) + '\n')

        logger.info(f"Exported {len(self.entries)} audit entries to {output_path}")
