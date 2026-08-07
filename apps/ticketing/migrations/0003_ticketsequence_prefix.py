"""
Give each event's ticket sequence its own stored, unique prefix.

Without this, the prefix was derived from the event's year at issue time, so two
events in the same year both started at TEDX2026-0001 and collided on
`Ticket.ticket_number`. Since the PRD explicitly requires supporting multiple
future events, that was reachable in normal use.

Written as add → backfill → constrain rather than a single AddField so it is
safe on a table that already has rows.
"""

from django.db import migrations, models


def backfill_prefixes(apps, schema_editor):
    """Derive a unique prefix for any sequence that predates this column."""
    TicketSequence = apps.get_model('ticketing', 'TicketSequence')

    taken = set()
    for sequence in TicketSequence.objects.select_related('event').order_by('pk'):
        event = sequence.event
        base = event.ticket_prefix or f'TEDX{event.start_datetime.year}'
        candidate, attempt = base, 1
        while candidate in taken:
            attempt += 1
            candidate = f'{base}-{attempt}'
        taken.add(candidate)
        sequence.prefix = candidate
        sequence.save(update_fields=['prefix'])


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('ticketing', '0002_roles'),
    ]

    operations = [
        migrations.AddField(
            model_name='ticketsequence',
            name='prefix',
            field=models.CharField(default='', max_length=40),
            preserve_default=False,
        ),
        migrations.RunPython(backfill_prefixes, noop),
        migrations.AlterField(
            model_name='ticketsequence',
            name='prefix',
            field=models.CharField(max_length=40, unique=True),
        ),
    ]
