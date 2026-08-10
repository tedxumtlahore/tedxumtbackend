"""
Payment providers.

A provider decides two things: what the attendee has to do to pay, and what
counts as proof they did. Everything downstream of payment — issuing the
ticket, the QR, the email — is provider-agnostic and lives in `services.py`.

Adding a real gateway later means writing one class here and registering it.
Nothing in the models, the API, or the check-in flow needs to change.

The one rule every provider must respect: **a client request can never be the
thing that marks an order paid.** A provider either settles the order itself
(because there is nothing to collect), or it hands off to something the
attendee does not control — a staff confirmation, or a signed webhook.
"""

from dataclasses import dataclass, field


@dataclass
class PaymentInstructions:
    """What the frontend should show the attendee after they register."""

    kind: str                       # 'none' | 'instructions' | 'redirect'
    message: str
    redirect_url: str = ''
    details: dict = field(default_factory=dict)

    def as_dict(self):
        return {
            'kind': self.kind,
            'message': self.message,
            'redirect_url': self.redirect_url,
            'details': self.details,
        }


class PaymentProvider:
    """Base class. Subclasses set `key` and `label` and override `start`."""

    key = ''
    label = ''

    #: True when the provider settles immediately and no money changes hands.
    settles_immediately = False

    def start(self, order):
        """Begin payment for `order`; return PaymentInstructions."""
        raise NotImplementedError

    def verify(self, order, payload):
        """
        Confirm an incoming provider callback.

        Real gateways must validate a signature over `payload` here and return
        False on any mismatch. The bundled providers have no callback, so the
        safe default is to refuse.
        """
        return False


class FreeProvider(PaymentProvider):
    """For events with `ticket_price == 0`. Settles instantly, collects nothing."""

    key = 'free'
    label = 'Free ticket'
    settles_immediately = True

    def start(self, order):
        return PaymentInstructions(
            kind='none',
            message='This event is free — your ticket has been issued.',
        )


class ManualTransferProvider(PaymentProvider):
    """
    Bank transfer confirmed by an organizer.

    The attendee transfers the fee and submits their bank reference. An
    organizer checks the bank statement and confirms in the admin, which is what
    actually issues the ticket. The attendee-supplied reference is a lookup aid
    for the organizer — it is never treated as proof of payment.
    """

    key = 'manual_transfer'
    label = 'Bank transfer (confirmed by organizers)'

    def start(self, order):
        from .models import PaymentAccount

        event = order.registration.event
        accounts = PaymentAccount.objects.filter(is_active=True, is_visible=True)

        return PaymentInstructions(
            kind='instructions',
            message=(
                f'Send {order.currency} {order.amount:.2f} to one of the accounts below, '
                'then come back and tell us the transaction ID. We will email your '
                'ticket once the payment is confirmed — usually within one working day.'
            ),
            details={
                'amount': f'{order.amount:.2f}',
                'currency': order.currency,
                'event': event.title,
                'accounts': [
                    {
                        'provider': account.provider,
                        'provider_label': account.get_provider_display(),
                        'account_title': account.account_title,
                        'account_number': account.account_number,
                        'bank_name': account.bank_name,
                        'iban': account.iban,
                        'note': account.note,
                    }
                    for account in accounts
                ],
            },
        )


_PROVIDERS = {
    provider.key: provider
    for provider in (FreeProvider(), ManualTransferProvider())
}


def get_provider(key):
    """Look up a provider, raising a clear error for an unknown key."""
    try:
        return _PROVIDERS[key]
    except KeyError:
        raise ValueError(f'Unknown payment provider {key!r}.') from None


def provider_for_event(event):
    """Free events settle themselves; everything else goes to manual transfer."""
    return _PROVIDERS[FreeProvider.key if event.is_free else ManualTransferProvider.key]


def available_providers():
    return [{'key': p.key, 'label': p.label} for p in _PROVIDERS.values()]
