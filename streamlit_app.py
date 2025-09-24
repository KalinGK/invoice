import streamlit as st
import anthropic
import json
import base64
from datetime import datetime
from PIL import Image
import io

# Page config
st.set_page_config(
    page_title="Invoice Data Extractor",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(90deg, #1e40af, #3b82f6);
        padding: 2rem;
        border-radius: 10px;
        color: white;
        text-align: center;
        margin-bottom: 2rem;
    }
    
    .invoice-card {
        background: white;
        padding: 1.5rem;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        margin-bottom: 1rem;
    }
    
    .status-outstanding {
        background-color: #fee2e2;
        color: #dc2626;
        padding: 0.25rem 0.75rem;
        border-radius: 9999px;
        font-size: 0.75rem;
        font-weight: 600;
        display: inline-block;
    }
    
    .status-paid {
        background-color: #dcfce7;
        color: #16a34a;
        padding: 0.25rem 0.75rem;
        border-radius: 9999px;
        font-size: 0.75rem;
        font-weight: 600;
        display: inline-block;
    }
    
    .amount-large {
        font-size: 2rem;
        font-weight: bold;
        color: #1f2937;
    }
    
    .section-header {
        color: #374151;
        font-weight: 600;
        font-size: 1.1rem;
        margin-bottom: 1rem;
        padding-bottom: 0.5rem;
        border-bottom: 2px solid #e5e7eb;
    }
</style>
""", unsafe_allow_html=True)

def encode_image(image_file):
    """Convert uploaded image to base64"""
    return base64.b64encode(image_file.read()).decode('utf-8')

def extract_invoice_data(image_base64, api_key):
    """Extract structured data from invoice image using Anthropic API"""
    
    client = anthropic.Anthropic(api_key=api_key)
    
    invoice_schema = {
        "invoice": {
            "header": {
                "invoice_number": "",
                "invoice_date": "",
                "due_date": "",
                "issuing_company": "",
                "currency": ""
            },
            "billing_parties": {
                "bill_to": {
                    "company_name": "",
                    "address": "",
                    "organization_number": "",
                    "vat_number": ""
                },
                "bill_from": {
                    "company_name": "",
                    "address": "",
                    "organization_number": "",
                    "vat_number": "",
                    "phone": "",
                    "email": "",
                    "reference": ""
                }
            },
            "line_items": [],
            "totals": {
                "subtotal": 0,
                "total_discount": 0,
                "total_vat": 0,
                "total_amount": 0,
                "amount_paid": 0,
                "balance_due": 0
            },
            "payment_info": {
                "bank_name": "",
                "iban": "",
                "swift_bic": "",
                "payment_reference": ""
            }
        }
    }
    
    try:
        response = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=4000,
            messages=[{
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/jpeg",
                            "data": image_base64
                        }
                    },
                    {
                        "type": "text",
                        "text": f"""Extract all invoice data from this image and return it in the following JSON structure. Be precise with numbers and dates. If information is not available, use empty string or 0 for numbers.

Required JSON structure:
{json.dumps(invoice_schema, indent=2)}

For line_items, each item should have:
- line_number (integer)
- description (string)
- quantity (number)
- unit_of_measure (string)
- unit_price (number)
- discount_percentage (number, as decimal like 0.05 for 5%)
- line_total (number)
- vat_rate (number, as decimal like 0.20 for 20%)
- vat_amount (number)

Return ONLY the JSON structure, no additional text."""
                    }
                ]
            }]
        )
        
        # Parse the JSON response
        json_text = response.content[0].text.strip()
        if json_text.startswith('```json'):
            json_text = json_text[7:]
        if json_text.endswith('```'):
            json_text = json_text[:-3]
            
        return json.loads(json_text)
        
    except Exception as e:
        st.error(f"Error extracting data: {str(e)}")
        return None

def display_invoice_data(data):
    """Display extracted invoice data in a nice format"""
    
    if not data or 'invoice' not in data:
        st.error("No invoice data to display")
        return
    
    invoice = data['invoice']
    
    # Header section
    st.markdown('<div class="main-header">', unsafe_allow_html=True)
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown(f"# INVOICE #{invoice['header'].get('invoice_number', 'N/A')}")
        st.markdown(f"**{invoice['header'].get('issuing_company', 'N/A')}**")
    
    with col2:
        st.markdown("### Amount Due")
        amount = invoice['totals'].get('total_amount', 0)
        currency = invoice['header'].get('currency', 'USD')
        st.markdown(f'<div class="amount-large">{amount:,.2f} {currency}</div>', unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Invoice details
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("**Invoice Date**")
        st.write(invoice['header'].get('invoice_date', 'N/A'))
    
    with col2:
        st.markdown("**Due Date**") 
        st.write(invoice['header'].get('due_date', 'N/A'))
    
    with col3:
        st.markdown("**Status**")
        balance_due = invoice['totals'].get('balance_due', 0)
        if balance_due > 0:
            st.markdown('<span class="status-outstanding">Outstanding</span>', unsafe_allow_html=True)
        else:
            st.markdown('<span class="status-paid">Paid</span>', unsafe_allow_html=True)
    
    # Billing parties
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown('<div class="invoice-card">', unsafe_allow_html=True)
        st.markdown('<div class="section-header">Bill From</div>', unsafe_allow_html=True)
        
        bill_from = invoice['billing_parties']['bill_from']
        st.markdown(f"**{bill_from.get('company_name', 'N/A')}**")
        if bill_from.get('address'):
            st.write(bill_from['address'])
        if bill_from.get('phone'):
            st.write(f"📞 {bill_from['phone']}")
        if bill_from.get('email'):
            st.write(f"📧 {bill_from['email']}")
        
        if bill_from.get('vat_number') or bill_from.get('organization_number'):
            st.markdown("---")
            if bill_from.get('vat_number'):
                st.write(f"VAT: {bill_from['vat_number']}")
            if bill_from.get('organization_number'):
                st.write(f"Org: {bill_from['organization_number']}")
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col2:
        st.markdown('<div class="invoice-card">', unsafe_allow_html=True)
        st.markdown('<div class="section-header">Bill To</div>', unsafe_allow_html=True)
        
        bill_to = invoice['billing_parties']['bill_to']
        st.markdown(f"**{bill_to.get('company_name', 'N/A')}**")
        if bill_to.get('address'):
            st.write(bill_to['address'])
        
        if bill_to.get('vat_number') or bill_to.get('organization_number'):
            st.markdown("---")
            if bill_to.get('vat_number'):
                st.write(f"VAT: {bill_to['vat_number']}")
            if bill_to.get('organization_number'):
                st.write(f"Org: {bill_to['organization_number']}")
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Line items
    st.markdown('<div class="section-header">Invoice Items</div>', unsafe_allow_html=True)
    
    if invoice.get('line_items'):
        items_data = []
        for item in invoice['line_items']:
            items_data.append({
                '#': item.get('line_number', ''),
                'Description': item.get('description', ''),
                'Qty': f"{item.get('quantity', 0)} {item.get('unit_of_measure', '')}".strip(),
                'Unit Price': f"{item.get('unit_price', 0):,.2f}",
                'Discount': f"{item.get('discount_percentage', 0)*100:.0f}%" if item.get('discount_percentage', 0) > 0 else "0%",
                'Subtotal': f"{item.get('line_total', 0):,.2f}",
                'VAT': f"{item.get('vat_amount', 0):,.2f} ({item.get('vat_rate', 0)*100:.0f}%)"
            })
        
        st.dataframe(items_data, use_container_width=True, hide_index=True)
    else:
        st.write("No line items found")
    
    # Summary and Payment Info
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown('<div class="invoice-card">', unsafe_allow_html=True)
        st.markdown('<div class="section-header">Payment Information</div>', unsafe_allow_html=True)
        
        payment_info = invoice.get('payment_info', {})
        if payment_info.get('bank_name'):
            st.write(f"**Bank:** {payment_info['bank_name']}")
        if payment_info.get('iban'):
            st.write(f"**IBAN:** `{payment_info['iban']}`")
        if payment_info.get('swift_bic'):
            st.write(f"**SWIFT/BIC:** `{payment_info['swift_bic']}`")
        if payment_info.get('payment_reference'):
            st.write(f"**Reference:** {payment_info['payment_reference']}")
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col2:
        st.markdown('<div class="invoice-card">', unsafe_allow_html=True)
        st.markdown('<div class="section-header">Invoice Summary</div>', unsafe_allow_html=True)
        
        totals = invoice['totals']
        currency = invoice['header'].get('currency', 'USD')
        
        summary_data = [
            ("Subtotal", f"{totals.get('subtotal', 0):,.2f} {currency}"),
            ("Total Discount", f"-{totals.get('total_discount', 0):,.2f} {currency}" if totals.get('total_discount', 0) > 0 else f"0.00 {currency}"),
            ("Total VAT", f"{totals.get('total_vat', 0):,.2f} {currency}"),
            ("**Total Amount**", f"**{totals.get('total_amount', 0):,.2f} {currency}**"),
            ("Amount Paid", f"{totals.get('amount_paid', 0):,.2f} {currency}"),
            ("**Balance Due**", f"**{totals.get('balance_due', 0):,.2f} {currency}**")
        ]
        
        for label, value in summary_data:
            col_a, col_b = st.columns([1, 1])
            with col_a:
                st.markdown(label)
            with col_b:
                if "Balance Due" in label and totals.get('balance_due', 0) > 0:
                    st.markdown(f'<span style="color: #dc2626;">{value}</span>', unsafe_allow_html=True)
                elif "Amount Paid" in label and totals.get('amount_paid', 0) > 0:
                    st.markdown(f'<span style="color: #16a34a;">{value}</span>', unsafe_allow_html=True)
                else:
                    st.markdown(value)
        
        st.markdown('</div>', unsafe_allow_html=True)

# Main app
def main():
    st.markdown('<div class="main-header"><h1>📄 Invoice Data Extractor</h1><p>Upload an invoice image and extract structured data using AI</p></div>', unsafe_allow_html=True)
    
    # Sidebar for API key
    with st.sidebar:
        st.markdown("### Configuration")
        api_key = st.text_input("Anthropic API Key", type="password", help="Enter your Anthropic API key")
        
        st.markdown("### Instructions")
        st.markdown("""
        1. Enter your Anthropic API key
        2. Upload an invoice image (JPG, PNG)
        3. Click 'Extract Data' to process
        4. View the structured results
        """)
        
        st.markdown("### Supported Formats")
        st.markdown("- JPEG/JPG images")
        st.markdown("- PNG images")
        st.markdown("- Multiple languages")
        st.markdown("- Various invoice layouts")
    
    # File upload - Multiple files
    uploaded_files = st.file_uploader(
        "Upload Invoice Images", 
        type=['jpg', 'jpeg', 'png'],
        help="Upload clear images of your invoices",
        accept_multiple_files=True
    )
    
    if uploaded_files:
        st.markdown(f"### {len(uploaded_files)} Invoice(s) Uploaded")
        
        # Initialize session state for multiple invoices
        if 'all_extracted_data' not in st.session_state:
            st.session_state.all_extracted_data = {}
        
        # Display uploaded images in a grid
        if len(uploaded_files) <= 3:
            cols = st.columns(len(uploaded_files))
        else:
            cols = st.columns(3)
        
        for idx, uploaded_file in enumerate(uploaded_files):
            col_idx = idx % 3 if len(uploaded_files) > 3 else idx
            with cols[col_idx]:
                image = Image.open(uploaded_file)
                st.image(image, caption=f"{uploaded_file.name[:20]}...", use_container_width=True)
                st.write(f"**Size:** {uploaded_file.size / 1024:.1f} KB")
        
        # Batch processing options
        col1, col2 = st.columns([1, 1])
        with col1:
            process_all = st.button("🔍 Process All Invoices", type="primary", use_container_width=True)
        with col2:
            selected_invoice = st.selectbox(
                "Or process individually:",
                options=["Select an invoice..."] + [f.name for f in uploaded_files]
            )
            process_single = st.button("🔍 Process Selected", use_container_width=True)
        
        # Process all invoices
        if process_all:
            if not api_key:
                st.error("Please enter your Anthropic API key in the sidebar")
                return
            
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            successful_extractions = 0
            failed_extractions = 0
            
            for idx, uploaded_file in enumerate(uploaded_files):
                status_text.text(f"Processing {uploaded_file.name}... ({idx + 1}/{len(uploaded_files)})")
                progress_bar.progress((idx + 1) / len(uploaded_files))
                
                try:
                    # Reset file pointer
                    uploaded_file.seek(0)
                    image_base64 = encode_image(uploaded_file)
                    
                    # Extract data
                    extracted_data = extract_invoice_data(image_base64, api_key)
                    
                    if extracted_data:
                        st.session_state.all_extracted_data[uploaded_file.name] = extracted_data
                        successful_extractions += 1
                    else:
                        failed_extractions += 1
                        
                except Exception as e:
                    st.error(f"Error processing {uploaded_file.name}: {str(e)}")
                    failed_extractions += 1
            
            status_text.text("Processing complete!")
            
            if successful_extractions > 0:
                st.success(f"✅ Successfully processed {successful_extractions} invoice(s)!")
                if failed_extractions > 0:
                    st.warning(f"⚠️ Failed to process {failed_extractions} invoice(s)")
            else:
                st.error("❌ Failed to process any invoices")
        
        # Process single invoice
        elif process_single and selected_invoice != "Select an invoice...":
            if not api_key:
                st.error("Please enter your Anthropic API key in the sidebar")
                return
            
            selected_file = next(f for f in uploaded_files if f.name == selected_invoice)
            
            with st.spinner(f"Processing {selected_invoice}..."):
                try:
                    # Reset file pointer
                    selected_file.seek(0)
                    image_base64 = encode_image(selected_file)
                    
                    # Extract data
                    extracted_data = extract_invoice_data(image_base64, api_key)
                    
                    if extracted_data:
                        st.session_state.all_extracted_data[selected_file.name] = extracted_data
                        st.success(f"✅ Successfully processed {selected_invoice}!")
                    else:
                        st.error(f"❌ Failed to process {selected_invoice}")
                        
                except Exception as e:
                    st.error(f"Error processing {selected_invoice}: {str(e)}")
        
        # Display extracted data
        if st.session_state.all_extracted_data:
            st.markdown("---")
            st.markdown("## 📋 Extracted Invoice Data")
            
            # Create tabs for each invoice
            if len(st.session_state.all_extracted_data) == 1:
                # Single invoice - display directly
                filename, data = next(iter(st.session_state.all_extracted_data.items()))
                st.markdown(f"### {filename}")
                display_invoice_data(data)
                
                # Download button
                json_str = json.dumps(data, indent=2, ensure_ascii=False)
                st.download_button(
                    label=f"📥 Download {filename} JSON",
                    data=json_str,
                    file_name=f"invoice_data_{filename}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                    mime="application/json",
                    use_container_width=True
                )
            
            else:
                # Multiple invoices - use tabs
                tab_names = list(st.session_state.all_extracted_data.keys())
                tabs = st.tabs([f"📄 {name[:15]}..." if len(name) > 15 else f"📄 {name}" for name in tab_names])
                
                for tab, filename in zip(tabs, tab_names):
                    with tab:
                        display_invoice_data(st.session_state.all_extracted_data[filename])
                        
                        # Individual download button
                        json_str = json.dumps(st.session_state.all_extracted_data[filename], indent=2, ensure_ascii=False)
                        st.download_button(
                            label=f"📥 Download JSON",
                            data=json_str,
                            file_name=f"invoice_data_{filename}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                            mime="application/json",
                            key=f"download_{filename}"
                        )
                
                # Bulk download button
                st.markdown("---")
                col1, col2 = st.columns([1, 1])
                
                with col1:
                    # Download all as single JSON
                    all_data = {"invoices": st.session_state.all_extracted_data}
                    all_json_str = json.dumps(all_data, indent=2, ensure_ascii=False)
                    st.download_button(
                        label="📥 Download All JSON Data",
                        data=all_json_str,
                        file_name=f"all_invoices_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                        mime="application/json",
                        use_container_width=True
                    )
                
                with col2:
                    # Create summary CSV
                    summary_data = []
                    for filename, data in st.session_state.all_extracted_data.items():
                        invoice = data.get('invoice', {})
                        summary_data.append({
                            'filename': filename,
                            'invoice_number': invoice.get('header', {}).get('invoice_number', ''),
                            'company': invoice.get('billing_parties', {}).get('bill_from', {}).get('company_name', ''),
                            'total_amount': invoice.get('totals', {}).get('total_amount', 0),
                            'currency': invoice.get('header', {}).get('currency', ''),
                            'balance_due': invoice.get('totals', {}).get('balance_due', 0),
                            'invoice_date': invoice.get('header', {}).get('invoice_date', ''),
                            'due_date': invoice.get('header', {}).get('due_date', '')
                        })
                    
                    import csv
                    import io
                    
                    csv_buffer = io.StringIO()
                    if summary_data:
                        writer = csv.DictWriter(csv_buffer, fieldnames=summary_data[0].keys())
                        writer.writeheader()
                        writer.writerows(summary_data)
                    
                    st.download_button(
                        label="📊 Download Summary CSV",
                        data=csv_buffer.getvalue(),
                        file_name=f"invoice_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                        mime="text/csv",
                        use_container_width=True
                    )
        
        # Clear data button
        if st.session_state.all_extracted_data:
            st.markdown("---")
            if st.button("🗑️ Clear All Data", type="secondary", use_container_width=True):
                st.session_state.all_extracted_data = {}
                st.rerun()
    
    # Display previously extracted data if available and no new files uploaded
    elif 'all_extracted_data' in st.session_state and st.session_state.all_extracted_data:
        st.info("Showing previously extracted data. Upload new invoices to process fresh data.")
        
        # Display in tabs if multiple, single view if one
        if len(st.session_state.all_extracted_data) == 1:
            filename, data = next(iter(st.session_state.all_extracted_data.items()))
            st.markdown(f"### Previous Result: {filename}")
            display_invoice_data(data)
        else:
            st.markdown("## 📋 Previously Extracted Data")
            tab_names = list(st.session_state.all_extracted_data.keys())
            tabs = st.tabs([f"📄 {name[:15]}..." if len(name) > 15 else f"📄 {name}" for name in tab_names])
            
            for tab, filename in zip(tabs, tab_names):
                with tab:
                    display_invoice_data(st.session_state.all_extracted_data[filename])

if __name__ == "__main__":
    main()
