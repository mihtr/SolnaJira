# Quick Start Guide - New Features

## Installation

1. Install the new dependency:
```bash
pip install -r requirements.txt
```

This will install `openpyxl>=3.1.0` (new requirement for Excel export).

---

## Feature 1: Logging Module

### What Changed
- All internal debug/info messages now use Python's logging module
- Log files automatically created in `./logs/` directory
- User-facing output (summaries, reports) still uses print statements

### Usage

**Standard logging (INFO level)**:
```bash
python extract_worklogs.py
```

**Debug logging (DEBUG level)**:
```bash
python extract_worklogs.py --log-level 2
```

### Log Files
- **Location**: `./logs/jira_extractor_YYYYMMDD_HHMMSS.log`
- **Rotation**: Automatically rotates at 10MB, keeps 10 backups
- **Content**: Timestamps, log levels, detailed operation info

---

## Feature 2: Excel Export

### What's New
Excel export with 9 comprehensive sheets:
1. Summary (overall statistics)
2. Hours by Year-Month
3. Hours by Product Item
4. Hours by Component
5. Hours by Label
6. Hours by Team
7. Hours by Author
8. Hours by Issue
9. All Worklog Entries (raw data)

### Usage

**Export Excel only**:
```bash
python extract_worklogs.py --format excel
```

**Export all formats (CSV + HTML + Excel)**:
```bash
python extract_worklogs.py --format all
```

**Other format options**:
- `--format csv` - CSV only
- `--format html` - HTML only
- `--format both` - CSV + HTML (default)

### Excel Features
- Professional formatting (colored headers, borders)
- Auto-sized columns
- Multiple aggregation views
- Same data as CSV/HTML reports

---

## Feature 3: Date Filtering (HTML Report)

### What's New
Interactive date range filter for the "Hours by Year/Month" chart in HTML reports.

### How to Use

1. **Generate HTML report**:
   ```bash
   python extract_worklogs.py --format html
   # or
   python extract_worklogs.py --format both  # default
   ```

2. **Open HTML report in browser**

3. **Navigate to "Hours by Year and Month" section**

4. **Use the date filter**:
   - Select "From" date (e.g., 2024-01)
   - Select "To" date (e.g., 2024-12)
   - Click "Apply Filter"
   - Chart updates to show only selected period
   - Filtered total hours displayed

5. **Reset filter**:
   - Click "Reset" button to restore all data

### Features
- Filter persists in browser (localStorage)
- Automatically applied when reopening report
- One-click reset to full data view
- Shows filtered total hours

---

## Complete Example

Run with all new features:

```bash
# Export all formats with debug logging
python extract_worklogs.py --format all --log-level 2 --output-dir ./reports

# Output:
# - ./reports/zyn_worklogs_20251205_143000.csv
# - ./reports/zyn_worklogs_20251205_143000.html (with date filtering)
# - ./reports/zyn_worklogs_20251205_143000.xlsx (9 sheets)
# - ./logs/jira_extractor_20251205_143000.log
```

---

## Troubleshooting

### Issue: "openpyxl not found"
**Solution**: Run `pip install -r requirements.txt`

### Issue: Excel export seems slow
**Normal**: Excel export takes longer than CSV (5-10 seconds for 1000 worklogs)

### Issue: Date filter doesn't work
**Check**:
1. Using HTML report (not CSV/Excel)
2. Browser supports `<input type="month">` (Chrome 20+, Firefox 57+, Safari 14.1+)
3. JavaScript is enabled

### Issue: Logs directory not created
**Check**: Run script at least once - directory created automatically

---

## Help

View all options:
```bash
python extract_worklogs.py --help
```

View version:
```bash
python extract_worklogs.py --version
```

---

For detailed implementation information, see `IMPLEMENTATION_SUMMARY.md`.
