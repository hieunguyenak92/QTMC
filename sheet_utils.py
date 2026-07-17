def ensure_worksheet_capacity(worksheet, required_rows, required_cols, row_buffer=1000):
    """Expand a worksheet before writing an explicit A1 range outside its grid."""
    current_rows = int(getattr(worksheet, 'row_count', 0) or 0)
    current_cols = int(getattr(worksheet, 'col_count', 0) or 0)
    if required_rows <= current_rows and required_cols <= current_cols:
        return

    target_rows = current_rows
    if required_rows > current_rows:
        target_rows = max(required_rows, current_rows + row_buffer)
    target_cols = max(required_cols, current_cols)
    worksheet.resize(rows=target_rows, cols=target_cols)
