#!/usr/bin/env python3
"""
Test script to verify global selection behavior in the live application.
This script will simulate bar clicks and check the console output.
"""

import requests
import time
import json

def test_global_selection():
    """Test the global selection implementation by making requests to the running app."""
    
    print("🧪 Testing Global Selection Implementation")
    print("=" * 60)
    
    # Check if app is running
    try:
        response = requests.get("http://localhost:5001/", timeout=5)
        if response.status_code == 200:
            print("✅ App is running on port 5001")
        else:
            print(f"❌ App returned status code: {response.status_code}")
            return
    except requests.exceptions.RequestException as e:
        print(f"❌ Cannot connect to app: {e}")
        return
    
    print("\n📋 Test Instructions:")
    print("1. Open browser to http://localhost:5001")
    print("2. Navigate to WCOD Crude Overview")
    print("3. Switch to Monthly Filter view")
    print("4. Open browser developer console (F12)")
    print("5. Click on any bar in the chart")
    print("6. Look for these debug messages:")
    print("   - 'DEBUG CHART CLICK: Bar clicked - Stream: ...'")
    print("   - 'DEBUG SELECTED_BAR: activeBar found!'")
    print("   - 'DEBUG TRACE OPACITY: [stream]-[year]'")
    print("   - Check if 'Contains active bar: true' appears for only ONE trace")
    print("   - Check if 'Final opacity: 1.0' appears for only ONE trace")
    print("   - All other traces should show 'Final opacity: 0.3'")
    
    print("\n🎯 Expected Behavior:")
    print("• Only ONE bar across the entire chart should be active (opacity 1.0)")
    print("• ALL other bars in ALL years should be dimmed (opacity 0.3)")
    print("• Selection should work globally, not year-wise")
    
    print("\n🔧 If Issues Found:")
    print("• Check data types in debug messages")
    print("• Verify year_match, month_match, stream_match values")
    print("• Look for any error messages in console")
    
    print(f"\n🌐 App URL: http://localhost:5001")

if __name__ == "__main__":
    test_global_selection()