# pdf_templates.py
from reportlab.lib.pagesizes import letter
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    Image,
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch

# Define custom styles
styles = getSampleStyleSheet()
styles.add(ParagraphStyle(name="RightAlign", alignment=2))
styles.add(ParagraphStyle(name="VendorHeader", fontSize=18, fontName="Helvetica-Bold"))
styles.add(
    ParagraphStyle(name="DocTitle", fontSize=22, fontName="Helvetica-Bold", alignment=1)
)


def draw_po_pdf(po_data, filename):
    """Generates the Purchase Order PDF."""
    doc = SimpleDocTemplate(filename, pagesize=letter)
    story = []

    # Header now shows the fictional buyer's name
    story.append(Paragraph(po_data["buyer_name"], styles["Heading1"]))
    story.append(
        Paragraph(po_data["buyer_address"].replace("\n", "<br/>"), styles["Normal"])
    )
    story.append(Spacer(1, 0.25 * inch))
    story.append(Paragraph("PURCHASE ORDER", styles["DocTitle"]))
    story.append(Spacer(1, 0.25 * inch))

    # PO Info Table
    vendor_address_formatted = po_data["vendor_address"].replace("\n", "<br/>")
    buyer_address_formatted = po_data["buyer_address"].replace("\n", "<br/>")
    info_data = [
        [
            Paragraph("<b>VENDOR</b>", styles["Normal"]),
            Paragraph("<b>SHIP TO</b>", styles["Normal"]),
        ],
        [
            Paragraph(
                f"{po_data['vendor_name']}<br/>{vendor_address_formatted}",
                styles["Normal"],
            ),
            Paragraph(
                f"{po_data['buyer_name']}<br/>{buyer_address_formatted}",
                styles["Normal"],
            ),
        ],
        ["", ""],  # Spacer row
        [
            Paragraph(
                f"<b>PO NUMBER:</b><br/>{po_data['po_number']}", styles["Normal"]
            ),
            Paragraph(
                f"<b>ORDER DATE:</b><br/>{po_data['order_date'].strftime('%B %d, %Y')}",
                styles["Normal"],
            ),
        ],
    ]
    info_table = Table(info_data, colWidths=[3 * inch, 3 * inch])
    info_table.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
    story.append(info_table)
    story.append(Spacer(1, 0.3 * inch))

    # Line Items - Now including pricing and totals
    item_data = [["SKU", "DESCRIPTION", "ORDERED QTY", "UNIT", "UNIT PRICE", "TOTAL"]]
    for item in po_data["line_items"]:
        item_data.append(
            [
                item["sku"],
                item["description"],
                item["ordered_qty"],
                item["unit"],
                f"${item['unit_price']:,.2f}",
                f"${item['line_total']:,.2f}",
            ]
        )

    item_table = Table(
        item_data,
        colWidths=[
            0.8 * inch,
            2.5 * inch,
            0.7 * inch,
            0.7 * inch,
            1 * inch,
            1.3 * inch,
        ],
    )
    item_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.darkblue),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("ALIGN", (4, 1), (-1, -1), "RIGHT"),  # Right align price columns
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                ("BACKGROUND", (0, 1), (-1, -1), colors.lightblue),
                ("GRID", (0, 0), (-1, -1), 1, colors.black),
            ]
        )
    )
    story.append(item_table)
    story.append(Spacer(1, 0.2 * inch))

    # PO Totals
    totals_data = [
        ["", "", "", "", "Subtotal:", f"${po_data['po_subtotal']:,.2f}"],
        ["", "", "", "", "Tax:", f"${po_data['po_tax']:,.2f}"],
        ["", "", "", "", "<b>TOTAL:</b>", f"<b>${po_data['po_grand_total']:,.2f}</b>"],
    ]
    totals_table = Table(
        totals_data,
        colWidths=[
            0.8 * inch,
            2.5 * inch,
            0.7 * inch,
            0.7 * inch,
            1 * inch,
            1.3 * inch,
        ],
    )
    totals_table.setStyle(
        TableStyle(
            [
                ("ALIGN", (4, 0), (-1, -1), "RIGHT"),
                ("LINEABOVE", (4, 0), (-1, 0), 1, colors.black),
                ("LINEABOVE", (4, 2), (-1, 2), 2, colors.black),
            ]
        )
    )
    story.append(totals_table)

    story.append(Spacer(1, 0.2 * inch))
    story.append(
        Paragraph(
            "<i>Note: This PO total represents the expected total value of all invoices. Multiple shipments and invoices may be issued against this PO.</i>",
            styles["Normal"],
        )
    )

    doc.build(story)


def draw_grn_pdf(po_data, grn_number, received_date, received_items, filename):
    """Generates the Goods Receipt Note PDF for a partial shipment."""
    doc = SimpleDocTemplate(filename, pagesize=letter)
    story = []

    # GRN is an internal document for the fictional buyer
    story.append(
        Paragraph(
            f"INTERNAL GOODS RECEIPT NOTE (GRN) - {po_data['buyer_name']}",
            styles["Heading1"],
        )
    )
    story.append(Spacer(1, 0.3 * inch))

    story.append(Paragraph(f"<b>GRN Number:</b> {grn_number}", styles["Normal"]))
    story.append(
        Paragraph(
            f"<b>Received Date:</b> {received_date.strftime('%Y-%m-%d')}",
            styles["Normal"],
        )
    )
    story.append(
        Paragraph(f"<b>Reference PO:</b> {po_data['po_number']}", styles["Normal"])
    )
    story.append(
        Paragraph(f"<b>Vendor:</b> {po_data['vendor_name']}", styles["Normal"])
    )
    story.append(Spacer(1, 0.3 * inch))

    story.append(
        Paragraph("<b>Items Received in this Shipment:</b>", styles["Heading3"])
    )

    item_data = [["SKU", "DESCRIPTION", "QTY RECEIVED", "UNIT"]]
    for item in received_items:
        item_data.append(
            [item["sku"], item["description"], item["received_qty"], item["unit"]]
        )

    item_table = Table(item_data, colWidths=[inch, 3.5 * inch, inch, inch])
    item_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                ("GRID", (0, 0), (-1, -1), 1, colors.black),
            ]
        )
    )
    story.append(item_table)
    story.append(Spacer(1, 0.75 * inch))

    story.append(
        Paragraph(
            "Signature: _________________________<br/>Printed Name: _____________________<br/>Dept: Warehouse/Receiving",
            styles["Normal"],
        )
    )

    doc.build(story)


def draw_invoice_pdf(
    invoice_data,
    invoice_number,
    invoice_date,
    due_date,
    filename,
    tax_override=None,
    grand_total_override=None,
):
    """Generates the Vendor Invoice PDF for a specific shipment."""
    doc = SimpleDocTemplate(filename, pagesize=letter)
    story = []

    # Vendor Header
    story.append(Paragraph(invoice_data["vendor_name"], styles["VendorHeader"]))
    story.append(
        Paragraph(
            invoice_data["vendor_address"].replace("\n", "<br/>"), styles["Normal"]
        )
    )
    story.append(Spacer(1, 0.5 * inch))

    story.append(Paragraph("INVOICE", styles["Heading1"]))
    story.append(Spacer(1, 0.2 * inch))

    buyer_address_formatted = invoice_data["buyer_address"].replace("\n", "<br/>")
    info_data = [
        [
            Paragraph(
                f"<b>BILL TO:</b><br/>{invoice_data['buyer_name']}<br/>{buyer_address_formatted}",
                styles["Normal"],
            ),
            Paragraph(
                f"<b>Invoice #:</b> {invoice_number}<br/>"
                f"<b>Date:</b> {invoice_date.strftime('%m/%d/%Y')}<br/>"
                f"<b>Due Date:</b> {due_date.strftime('%m/%d/%Y')}",
                styles["RightAlign"],
            ),
        ]
    ]
    story.append(Table(info_data, colWidths=[3.5 * inch, 3 * inch]))
    story.append(Spacer(1, 0.1 * inch))

    # Handle multiple PO numbers
    po_numbers = invoice_data.get(
        "related_po_numbers", [invoice_data.get("po_number", "N/A")]
    )
    if po_numbers and po_numbers != ["N/A"]:
        po_text = ", ".join(po_numbers) if len(po_numbers) > 1 else po_numbers[0]
    else:
        po_text = "N/A"
    story.append(Paragraph(f"<b>Reference PO(s): {po_text}</b>", styles["Normal"]))

    # Handle multiple GRN numbers
    grn_numbers = invoice_data.get(
        "related_grn_numbers", [invoice_data.get("grn_number", "N/A")]
    )
    if grn_numbers and grn_numbers != ["N/A"]:
        grn_text = ", ".join(grn_numbers) if len(grn_numbers) > 1 else grn_numbers[0]
    else:
        grn_text = "N/A"
    story.append(Paragraph(f"<b>Reference GRN(s): {grn_text}</b>", styles["Normal"]))
    story.append(Spacer(1, 0.3 * inch))

    item_data = [["DESCRIPTION", "QTY", "UNIT PRICE", "AMOUNT"]]
    for item in invoice_data["line_items"]:
        # Handle flexible field names
        qty = item.get("quantity", item.get("billed_qty", 0))
        amount = item.get("line_total", item.get("total", 0))
        item_data.append(
            [item["description"], qty, f"${item['unit_price']:,.2f}", f"${amount:,.2f}"]
        )

    item_table = Table(item_data, colWidths=[3.5 * inch, 0.5 * inch, inch, 1.5 * inch])
    item_table.setStyle(
        TableStyle(
            [
                ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
                ("LINEBELOW", (0, 0), (-1, 0), 2, colors.black),
                ("LINEBELOW", (0, -1), (-1, -1), 2, colors.black),
            ]
        )
    )
    story.append(item_table)
    story.append(Spacer(1, 0.1 * inch))

    # Calculate totals from invoice data
    subtotal = sum(
        item.get("line_total", item.get("total", 0))
        for item in invoice_data["line_items"]
    )

    # Use overrides if provided (for testing financial mismatches)
    if tax_override is not None:
        tax = tax_override
    else:
        tax = subtotal * 0.088  # Use a generic tax rate for calculation

    if grand_total_override is not None:
        grand_total = grand_total_override
    else:
        grand_total = subtotal + tax

    totals_data = [
        ["Subtotal", f"${subtotal:,.2f}"],
        ["Sales Tax", f"${tax:,.2f}"],
        ["<b>TOTAL DUE</b>", f"<b>${grand_total:,.2f}</b>"],
    ]
    totals_table = Table(
        totals_data, colWidths=[1.5 * inch, 1.5 * inch], hAlign="RIGHT"
    )
    totals_table.setStyle(TableStyle([("ALIGN", (0, 0), (-1, -1), "RIGHT")]))
    story.append(totals_table)

    doc.build(story)


# --- NEW MARKDOWN GENERATION FUNCTIONS ---


def draw_po_md(po_data, filename):
    """Generates the Purchase Order as a Markdown file."""
    content = []
    content.append(f"# PURCHASE ORDER: {po_data['po_number']}\n")
    content.append(f"**Order Date:** {po_data['order_date'].strftime('%B %d, %Y')}\n")

    content.append("---")

    content.append("\n## Parties\n")
    content.append(f"**Vendor:**\n")
    content.append(f"{po_data['vendor_name']}\n")
    vendor_address_md = po_data["vendor_address"].replace(chr(10), "  \n")
    content.append(f"{vendor_address_md}\n")  # Add Markdown line breaks

    content.append(f"\n**Ship To / Buyer:**\n")
    content.append(f"{po_data['buyer_name']}\n")
    buyer_address_md = po_data["buyer_address"].replace(chr(10), "  \n")
    content.append(f"{buyer_address_md}\n")

    content.append("---\n")

    content.append("## Ordered Items\n")
    # Table Header - Now including pricing and totals
    content.append("| SKU | Description | Ordered Qty | Unit | Unit Price | Total |")
    content.append("|:----|:------------|:-----------:|:-----|----------:|------:|")
    # Table Rows
    for item in po_data["line_items"]:
        content.append(
            f"| {item['sku']} | {item['description']} | {item['ordered_qty']} | {item['unit']} | ${item['unit_price']:,.2f} | ${item['line_total']:,.2f} |"
        )

    content.append("\n---\n")

    # PO Totals
    content.append(f"**Subtotal:** ${po_data['po_subtotal']:,.2f}\n")
    content.append(f"**Tax:** ${po_data['po_tax']:,.2f}\n")
    content.append(f"### **PO TOTAL: ${po_data['po_grand_total']:,.2f}**\n")

    content.append("---\n")
    content.append(
        "*Note: This PO total represents the expected total value of all invoices. Multiple shipments and invoices may be issued against this PO.*"
    )

    with open(filename, "w") as f:
        f.write("\n".join(content))
    print(f"  -> MD PO created: {filename}")


def draw_grn_md(po_data, grn_number, received_date, received_items, filename):
    """Generates the Goods Receipt Note as a Markdown file."""
    content = []
    content.append(f"# Goods Receipt Note (GRN): {grn_number}\n")
    content.append(f"**Reference PO:** `{po_data['po_number']}`\n")
    content.append(f"**Vendor:** {po_data['vendor_name']}\n")
    content.append(f"**Received Date:** {received_date.strftime('%Y-%m-%d')}\n")

    content.append("---\n")

    content.append("## Items Received in Shipment\n")
    content.append("| SKU | Description | Qty Received | Unit |")
    content.append("|:----|:------------|:------------:|:-----|")
    for item in received_items:
        content.append(
            f"| {item['sku']} | {item['description']} | {item['received_qty']} | {item['unit']} |"
        )

    content.append("\n\n---\n")
    content.append("**Received By:**\n\n____________________\n")
    content.append("Warehouse Department")

    with open(filename, "w") as f:
        f.write("\n".join(content))
    print(f"  -> MD GRN created: {filename}")


def draw_invoice_md(invoice_data, invoice_number, invoice_date, due_date, filename):
    """Generates the Vendor Invoice as a Markdown file."""
    content = []
    content.append(f"# INVOICE: {invoice_number}\n")
    content.append(f"## From: {invoice_data['vendor_name']}\n")

    content.append(f"**Invoice Date:** {invoice_date.strftime('%Y-%m-%d')}\n")
    content.append(f"**Due Date:** {due_date.strftime('%Y-%m-%d')}\n")
    content.append(f"**Reference PO:** `{invoice_data.get('po_number', 'N/A')}`\n")
    content.append(f"**Reference GRN:** `{invoice_data.get('grn_number', 'N/A')}`\n")

    content.append("\n---\n")

    content.append(f"### Bill To:\n")
    content.append(f"{invoice_data['buyer_name']}\n")
    buyer_address_md = invoice_data["buyer_address"].replace(chr(10), "  \n")
    content.append(f"{buyer_address_md}\n")

    content.append("---\n")

    content.append("### Billed Items\n")
    content.append("| Description | Qty | Unit Price | Amount |")
    content.append("|:------------|:---:|-----------:|-------:|")

    subtotal = 0
    for item in invoice_data["line_items"]:
        line_total = round(item["billed_qty"] * item["unit_price"], 2)
        subtotal += line_total
        content.append(
            f"| {item['description']} | {item['billed_qty']} | ${item['unit_price']:,.2f} | ${line_total:,.2f} |"
        )

    tax_rate = 0.088  # Use a consistent rate for display
    tax = subtotal * tax_rate
    grand_total = subtotal + tax

    content.append("\n---\n")
    content.append(f"**Subtotal:** ${subtotal:,.2f}\n")
    content.append(f"**Tax:** ${tax:,.2f}\n")
    content.append(f"### Total Due: ${grand_total:,.2f}\n")

    with open(filename, "w") as f:
        f.write("\n".join(content))
    print(f"  -> MD Invoice created: {filename}")
