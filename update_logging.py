"""
Script to replace print statements with logger calls in extract_worklogs.py
"""
import re

def replace_print_with_logger(content):
    """Replace print statements with appropriate logger calls"""

    # Patterns to identify print types
    # Debug prints (those with [DEBUG] prefix or within log_level >= 2 blocks)
    content = re.sub(
        r'print\(f"\[DEBUG\] ([^"]+)"\)',
        r'self.logger.debug(f"\1")',
        content
    )
    content = re.sub(
        r"print\(f'\[DEBUG\] ([^']+)'\)",
        r"self.logger.debug(f'\1')",
        content
    )

    # Warning prints (those with Warning: or [!] prefix)
    content = re.sub(
        r'print\(f?"?\s*Warning: ([^")]+)"\)',
        r'self.logger.warning("\1")',
        content
    )
    content = re.sub(
        r'print\(f"\s*\[!\] Warning: ([^"]+)"\)',
        r'self.logger.warning(f"\1")',
        content
    )
    content = re.sub(
        r"print\(f'\s*\[!\] Warning: ([^']+)'\)",
        r"self.logger.warning(f'\1')",
        content
    )

    # Error prints (those with Error: or ERROR prefix)
    content = re.sub(
        r'print\(f?"?\s*Error: ([^")]+)"\)',
        r'self.logger.error("\1")',
        content
    )
    content = re.sub(
        r'print\(f"\s*\[ERROR\] ([^"]+)"\)',
        r'self.logger.error(f"\1")',
        content
    )

    # Info prints - but preserve user-facing output (summary, reports, etc.)
    # We need to be selective here - only replace non-user-facing prints

    # Cache-related info
    content = re.sub(
        r'(\s+)if self\.log_level >= 1:\s+print\(f?"?([^)]+)"\)',
        r'\1self.logger.info(\2)',
        content
    )

    # Standard informational messages within methods
    # But we need to preserve print statements in validate_configuration and main()
    # that are user-facing

    return content

def main():
    # Read the file
    with open('extract_worklogs.py', 'r', encoding='utf-8-sig') as f:
        content = f.read()

    print("Original file loaded. Starting replacements...")

    # Backup original
    with open('extract_worklogs.py.bak', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Backup created: extract_worklogs.py.bak")

    # Do replacements
    content = replace_print_with_logger(content)

    # Write back
    with open('extract_worklogs.py', 'w', encoding='utf-8') as f:
        f.write(content)

    print("Replacements complete!")
    print("\nNext step: Manual review needed for user-facing print statements")
    print("- Validation output (validate_configuration)")
    print("- Summary reports (generate_summary)")
    print("- Main execution output (main function)")

if __name__ == "__main__":
    main()
