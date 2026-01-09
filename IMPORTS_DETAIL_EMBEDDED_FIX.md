# Imports Detail Embedded Issues Fix

## Issues Fixed

### 1. DataTable Invalid Column Properties
**Problem**: DataTable was showing React prop type errors for invalid column properties:
- `Warning: Failed prop type: Invalid prop 'header_styles' supplied to DataTable`
- `Warning: Failed prop type: Invalid prop 'cell_styles' supplied to DataTable`

**Root Cause**: In the `create_imports_table()` function, dynamic columns were being created with invalid properties `header_styles` and `cell_styles` which are not valid DataTable column properties.

**Solution**: Removed the invalid properties from the column definitions:
```python
# BEFORE (invalid)
dynamic_columns.append({
    'name': header_name,
    'id': col_id,
    'type': 'numeric',
    'format': {'specifier': ',.1f'},
    'presentation': 'input',
    'header_styles': {'textAlign': 'center'},    # INVALID
    'cell_styles': {'textAlign': 'right'}        # INVALID
})

# AFTER (fixed)
dynamic_columns.append({
    'name': header_name,
    'id': col_id,
    'type': 'numeric',
    'format': {'specifier': ',.1f'},
    'presentation': 'input'
})
```

**Note**: The styling for headers and cells is properly handled through the DataTable's `style_header` and `style_data_conditional` properties in the layout.

### 2. Dropdown Width Issue in Embedded Mode
**Problem**: The "Select Importing Country" dropdown had a fixed width of 1200px, causing it to extend outside the embedded page container.

**Solution**: Changed the dropdown to use responsive width:
```python
# BEFORE (fixed width)
style={
    'width': '1200px',
    # ... other styles
}

# AFTER (responsive width)
style={
    'width': '100%',
    'maxWidth': '400px',
    # ... other styles
}
```

## Files Modified
- `energy/app/dashboards/wcod/imports_detail.py`

## Testing
After these changes:
1. ✅ DataTable no longer shows React prop type warnings
2. ✅ Dropdown stays within embedded container bounds
3. ✅ All existing functionality preserved
4. ✅ Table styling remains consistent

## Impact
- Eliminates console warnings in embedded mode
- Improves layout compatibility with host applications
- Maintains all existing table functionality and styling