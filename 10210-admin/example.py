#!/usr/bin/env python3
"""
Test script to see QR code bytes and prepare for HTML usage
"""

import base64
from test import get_qr_code, QRCodeError

def inspect_qr_bytes():
    """Inspect QR code bytes and show different formats"""
    
    try:
        print("🔍 Getting QR code bytes...")
        qr_data = get_qr_code(session_name="default", save_to_file="test_qr.png")
        
        print("\n" + "="*60)
        print("📊 QR CODE BYTES INSPECTION")
        print("="*60)
        
        # 1. Basic info
        print(f"📏 Size: {len(qr_data)} bytes")
        print(f"🔢 Type: {type(qr_data)}")
        
        # 2. First 50 bytes as hex (to see PNG header)
        print(f"\n🔍 First 50 bytes (hex):")
        hex_preview = qr_data[:50].hex()
        formatted_hex = ' '.join(hex_preview[i:i+2] for i in range(0, len(hex_preview), 2))
        print(formatted_hex)
        
        # 3. PNG signature check
        png_signature = qr_data[:8]
        expected_png = b'\x89PNG\r\n\x1a\n'
        is_valid_png = png_signature == expected_png
        print(f"\n✅ PNG Signature: {'Valid' if is_valid_png else 'Invalid'}")
        print(f"   Expected: {expected_png.hex()}")
        print(f"   Got:      {png_signature.hex()}")
        
        # 4. Base64 encoded version (for HTML)
        base64_data = base64.b64encode(qr_data).decode('utf-8')
        print(f"\n📝 Base64 length: {len(base64_data)} characters")
        print(f"🔍 Base64 preview (first 100 chars):")
        print(base64_data[:100] + "...")
        
        # 5. HTML data URL format
        data_url = f"data:image/png;base64,{base64_data}"
        print(f"\n🌐 HTML Data URL length: {len(data_url)} characters")
        print(f"🔍 Data URL preview (first 150 chars):")
        print(data_url[:150] + "...")
        
        # 6. Save different formats for testing
        save_formats(qr_data, base64_data, data_url)
        
        return qr_data, base64_data, data_url
        
    except QRCodeError as e:
        print(f"❌ Error getting QR code: {e}")
        return None, None, None

def save_formats(qr_data, base64_data, data_url):
    """Save QR code in different formats for testing"""
    
    print("\n💾 Saving test files...")
    
    # 1. Raw binary file
    with open("qr_raw.png", "wb") as f:
        f.write(qr_data)
    print("   ✅ qr_raw.png (binary PNG file)")
    
    # 2. Base64 text file
    with open("qr_base64.txt", "w") as f:
        f.write(base64_data)
    print("   ✅ qr_base64.txt (base64 text)")
    
    # 3. HTML test file
    html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>QR Code Test</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; }}
        .qr-container {{ text-align: center; margin: 20px 0; }}
        .qr-image {{ border: 2px solid #ccc; border-radius: 10px; }}
        .info {{ background: #f5f5f5; padding: 15px; border-radius: 5px; margin: 10px 0; }}
    </style>
</head>
<body>
    <h1>🔍 QR Code Display Test</h1>
    
    <div class="info">
        <h3>📊 QR Code Info:</h3>
        <p><strong>Size:</strong> {len(qr_data)} bytes</p>
        <p><strong>Base64 Length:</strong> {len(base64_data)} characters</p>
        <p><strong>Data URL Length:</strong> {len(data_url)} characters</p>
    </div>
    
    <div class="qr-container">
        <h3>📱 QR Code Image (from bytes):</h3>
        <img src="{data_url}" alt="QR Code" class="qr-image" />
        <p><em>Scan this with your WhatsApp mobile app</em></p>
    </div>
    
    <div class="info">
        <h3>🔍 Technical Details:</h3>
        <p><strong>Data URL Format:</strong></p>
        <code>data:image/png;base64,[base64_data]</code>
        
        <p><strong>First 200 chars of base64:</strong></p>
        <code style="word-break: break-all; font-size: 12px;">
            {base64_data[:200]}...
        </code>
    </div>
    
    <div class="info">
        <h3>✅ Usage in Your App:</h3>
        <pre><code># Python: Convert bytes to data URL
import base64
qr_data = get_qr_code(session_name="default")
base64_str = base64.b64encode(qr_data).decode('utf-8')
data_url = f"data:image/png;base64,{{base64_str}}"

# HTML: Use as image source
&lt;img src="{{{{ data_url }}}}" alt="QR Code" /&gt;</code></pre>
    </div>
</body>
</html>
"""
    
    with open("qr_test.html", "w", encoding='utf-8') as f:
        f.write(html_content)
    print("   ✅ qr_test.html (HTML test page)")

def test_html_usage():
    """Show how to use QR bytes in HTML"""
    
    print("\n" + "="*60)
    print("🌐 HTML USAGE EXAMPLES")
    print("="*60)
    
    print("""
1. 📱 DIRECT USAGE (from bytes):
   
   # Get QR code bytes
   qr_data = get_qr_code(session_name="default")
   
   # Convert to base64 for HTML
   import base64
   base64_str = base64.b64encode(qr_data).decode('utf-8')
   data_url = f"data:image/png;base64,{base64_str}"
   
   # Use in HTML
   <img src="{data_url}" alt="QR Code" />

2. 🔧 IN FLASK/DJANGO:
   
   # Flask route
   @app.route('/qr')
   def get_qr():
       qr_data = get_qr_code(session_name="default")
       base64_str = base64.b64encode(qr_data).decode('utf-8')
       return render_template('qr.html', qr_data_url=f"data:image/png;base64,{base64_str}")
   
   # Template: qr.html
   <img src="{{ qr_data_url }}" alt="WhatsApp QR Code" />

3. 📤 AS API RESPONSE:
   
   # Return base64 in JSON
   {
       "qr_code": "iVBORw0KGgoAAAANSUhEUgAA...",
       "format": "png",
       "data_url": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAA..."
   }

4. 💾 SAVE AND SERVE:
   
   # Save file and serve static URL
   get_qr_code(session_name="default", save_to_file="static/qr.png")
   # HTML: <img src="/static/qr.png" alt="QR Code" />
""")

def main():
    """Main test function"""
    print("🧪 TESTING QR CODE BYTES & HTML USAGE")
    print("="*60)
    
    # Inspect the bytes
    qr_data, base64_data, data_url = inspect_qr_bytes()
    
    if qr_data:
        # Show HTML usage examples
        test_html_usage()
        
        print("\n📋 FILES CREATED:")
        print("   • qr_raw.png      - Binary PNG file")
        print("   • qr_base64.txt   - Base64 text")
        print("   • qr_test.html    - HTML test page")
        print("   • test_qr.png     - Additional PNG copy")
        
        print("\n🎯 NEXT STEPS:")
        print("   1. Open qr_test.html in your browser")
        print("   2. Check if QR code displays correctly")
        print("   3. Try scanning with WhatsApp mobile app")
        print("   4. Use the base64/data_url format in your app")
        
        return True
    else:
        print("❌ Could not get QR code for testing")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)