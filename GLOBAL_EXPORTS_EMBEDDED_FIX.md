# Global Exports Embedded Layout Fix

## Issue Fixed

**Problem**: After embedding the global exports page, the right-side filter section shifted to the center, disrupting the intended left-right layout.

**Root Cause**: The layout was using Bootstrap CSS classes (`col-md-9`, `col-md-3`, `row`) which can behave inconsistently in embedded environments where Bootstrap CSS may not be available or may conflict with the host application's styles.

## Solution

Replaced all Bootstrap CSS classes with explicit CSS styling using inline-block layout to ensure consistent behavior in embedded environments.

### Changes Made

#### 1. Map Section (Left Side - 75% width)
```python
# BEFORE
className="col-md-9",
style={"padding": "10px 5px 10px 10px", "maxWidth": "100%", "boxSizing": "border-box"}

# AFTER
style={
    "width": "75%",
    "display": "inline-block",
    "verticalAlign": "top",
    "padding": "10px 5px 10px 10px",
    "boxSizing": "border-box"
}
```

#### 2. Year Controls & Country Filter (Right Side - 25% width)
```python
# BEFORE
className="col-md-3",
style={"padding": "10px", "maxWidth": "100%", "boxSizing": "border-box"}

# AFTER
style={
    "width": "25%",
    "display": "inline-block",
    "verticalAlign": "top",
    "padding": "10px",
    "boxSizing": "border-box"
}
```

#### 3. Chart Section (Left Side - 75% width)
```python
# BEFORE
className="col-md-9",
style={"padding": "10px", "maxWidth": "100%", "boxSizing": "border-box"}

# AFTER
style={
    "width": "75%",
    "display": "inline-block",
    "verticalAlign": "top",
    "padding": "10px",
    "boxSizing": "border-box"
}
```

#### 4. Stream Filter (Right Side - 25% width)
```python
# BEFORE
className="col-md-3",
style={
    "padding": "25px 10px",
    # ... other styles
    "marginLeft": "0",
    "maxWidth": "100%",
    "boxSizing": "border-box",
}

# AFTER
style={
    "width": "25%",
    "display": "inline-block",
    "verticalAlign": "top",
    "padding": "25px 10px",
    # ... other styles (unchanged)
    "boxSizing": "border-box",
}
```

#### 5. Row Containers
```python
# BEFORE
className="row",
style={"marginLeft": "0", "marginRight": "0", "width": "100%"}

# AFTER
style={"width": "100%", "minWidth": "1200px", "overflowX": "auto"}
```

#### 6. Table Section
```python
# BEFORE
className="col-md-9",
style={"padding": "10px"}

# AFTER
style={"padding": "10px", "width": "100%"}
```

## Key Layout Principles Applied

1. **Explicit Width Control**: Used percentage-based widths (75%/25%) instead of Bootstrap's responsive grid
2. **Inline-Block Layout**: Used `display: inline-block` with `verticalAlign: top` for consistent side-by-side positioning
3. **Minimum Width**: Added `minWidth: "1200px"` to containers to ensure layout doesn't break on smaller screens
4. **Box Sizing**: Maintained `boxSizing: border-box` for predictable sizing behavior

## Files Modified
- `energy/app/dashboards/wcod/global_exports.py`

## Testing
After these changes:
1. ✅ Left-right layout remains consistent in embedded mode
2. ✅ Map section stays at 75% width on the left
3. ✅ Filter sections stay at 25% width on the right
4. ✅ All existing functionality preserved
5. ✅ No dependency on external Bootstrap CSS

## Impact
- Ensures consistent layout behavior in embedded environments
- Eliminates dependency on Bootstrap CSS classes
- Maintains responsive design while being more predictable
- Improves compatibility with various host applications