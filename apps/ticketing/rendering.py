"""
Ticket rendering — QR images and printable PDFs.

Everything here is generated **on demand and never written to disk**. That is
deliberate: the deployment target has an ephemeral filesystem, so a stored PDF
would silently vanish on the next deploy and an attendee's ticket would 404 at
the door. Regenerating from the database is cheap and always correct.

A ticket rendered here is derived entirely from `Ticket` + its registration, so
the output can never drift from what check-in will accept.
"""

import io

import qrcode
from django.utils import timezone
from reportlab.lib.colors import HexColor, white
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

TED_RED = HexColor('#E1062C')
INK = HexColor('#111111')
MUTED = HexColor('#6B6B6B')
HAIRLINE = HexColor('#DDDDDD')


#: The QR specification's minimum quiet zone, in modules. Do not lower this.
#: Verified empirically: a 2- or 3-module border fails to decode with OpenCV's
#: detector even at high resolution, while 4 decodes reliably. A code that a
#: scanner cannot read is discovered at the door on event day, so the margin is
#: not worth shaving.
QR_QUIET_ZONE = 4


def qr_png(payload, *, box_size=10, border=QR_QUIET_ZONE):
    """
    Render `payload` as a PNG and return the bytes.

    Error correction is set to Q (~25% recoverable) rather than the default M:
    a ticket gets folded, screenshotted, and scanned off a cracked phone screen
    in bad lighting, and the extra redundancy costs only a slightly denser code.
    """
    code = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_Q,
        box_size=box_size,
        border=border,
    )
    code.add_data(payload)
    code.make(fit=True)

    image = code.make_image(fill_color='black', back_color='white')
    buffer = io.BytesIO()
    image.save(buffer, format='PNG')
    return buffer.getvalue()


def _draw_wrapped(pdf, text, x, y, width, *, leading=13, font='Helvetica', size=10):
    """Minimal word wrap — reportlab has no flow model on a raw canvas."""
    pdf.setFont(font, size)
    words = str(text or '').split()
    line, cursor_y = '', y
    for word in words:
        candidate = f'{line} {word}'.strip()
        if pdf.stringWidth(candidate, font, size) <= width:
            line = candidate
            continue
        pdf.drawString(x, cursor_y, line)
        cursor_y -= leading
        line = word
    if line:
        pdf.drawString(x, cursor_y, line)
        cursor_y -= leading
    return cursor_y


# The page is sized to the ticket rather than to A4. Most of these are read on
# a phone, where an A4 sheet with the content crammed into the top third looks
# broken; and when printed, viewers offer fit-to-page anyway.
TICKET_PAGESIZE = (200 * mm, 95 * mm)


def ticket_pdf(ticket, *, qr_payload):
    """
    Build the printable ticket and return the PDF bytes.

    `qr_payload` is passed in rather than derived here so the PDF always encodes
    the same absolute URL the API handed the attendee — this module has no
    request object and must not guess at the host.
    """
    registration = ticket.registration
    event = registration.event
    venue = getattr(event, 'venue', None)

    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=TICKET_PAGESIZE)
    width, height = TICKET_PAGESIZE
    pdf.setTitle(f'{ticket.ticket_number} — {event.title}')
    pdf.setAuthor('TEDxUMT Lahore')

    margin = 12 * mm
    qr_size = 40 * mm
    qr_x = width - margin - qr_size
    text_width = qr_x - margin - 8 * mm

    # ── Header band ────────────────────────────────────────────────────────
    band = 20 * mm
    pdf.setFillColor(INK)
    pdf.rect(0, height - band, width, band, stroke=0, fill=1)

    baseline = height - 13 * mm
    pdf.setFillColor(white)
    pdf.setFont('Helvetica-Bold', 17)
    pdf.drawString(margin, baseline, 'TED')
    ted_width = pdf.stringWidth('TED', 'Helvetica-Bold', 17)
    pdf.setFillColor(TED_RED)
    pdf.drawString(margin + ted_width, baseline, 'x')
    x_width = pdf.stringWidth('x', 'Helvetica-Bold', 17)
    pdf.setFillColor(white)
    pdf.drawString(margin + ted_width + x_width, baseline, 'UMT Lahore')

    pdf.setFont('Helvetica-Bold', 11.5)
    pdf.drawRightString(width - margin, baseline, ticket.ticket_number)
    pdf.setFont('Helvetica', 6.5)
    pdf.setFillColor(HexColor('#AAAAAA'))
    pdf.drawRightString(width - margin, baseline - 4.5 * mm, 'ADMIT ONE')

    # ── Event title ────────────────────────────────────────────────────────
    y = height - band - 9 * mm
    pdf.setFillColor(INK)
    y = _draw_wrapped(pdf, event.title, margin, y, text_width,
                      leading=16, font='Helvetica-Bold', size=14)

    # ── Details ────────────────────────────────────────────────────────────
    y -= 3 * mm
    rows = [
        ('ATTENDEE', registration.full_name),
        ('DATE', timezone.localtime(event.start_datetime).strftime('%A, %d %B %Y — %I:%M %p')
                 if event.start_datetime else 'To be announced'),
        ('VENUE', f'{venue.name}, {venue.address}' if venue and venue.address
                  else (venue.name if venue else 'To be announced')),
    ]
    for label, value in rows:
        pdf.setFillColor(MUTED)
        pdf.setFont('Helvetica-Bold', 6.5)
        pdf.drawString(margin, y, label)
        pdf.setFillColor(INK)
        y = _draw_wrapped(pdf, value, margin, y - 4.2 * mm, text_width, leading=10.5, size=9)
        y -= 1.6 * mm

    # ── QR block ───────────────────────────────────────────────────────────
    qr_y = height - band - 6 * mm - qr_size
    pdf.drawImage(
        ImageReader(io.BytesIO(qr_png(qr_payload, box_size=8))),
        qr_x, qr_y, width=qr_size, height=qr_size,
    )
    pdf.setFillColor(MUTED)
    pdf.setFont('Helvetica', 6.5)
    pdf.drawCentredString(qr_x + qr_size / 2, qr_y - 4 * mm, 'Scan at the entrance')

    # ── Footer ─────────────────────────────────────────────────────────────
    footer_y = 8 * mm
    pdf.setStrokeColor(HAIRLINE)
    pdf.setLineWidth(0.6)
    pdf.line(margin, footer_y + 6.5 * mm, width - margin, footer_y + 6.5 * mm)

    pdf.setFillColor(MUTED)
    pdf.setFont('Helvetica', 6.5)
    pdf.drawString(
        margin, footer_y + 2.5 * mm,
        'Admits one person and is scanned once — please do not share it. Bring photo ID.',
    )
    pdf.drawString(
        margin, footer_y - 0.5 * mm,
        f'Registration {registration.public_ref}  ·  '
        'This independent TEDx event is operated under license from TED.',
    )

    pdf.showPage()
    pdf.save()
    return buffer.getvalue()
