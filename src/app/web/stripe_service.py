"""
stripe_service — integração com Stripe para cobranças e assinaturas.

Funcionalidades:
  - create_checkout_session: inicia pagamento de um plano
  - create_customer_portal_session: portal de autoatendimento do cliente
  - handle_webhook_event: processa eventos do Stripe (subscription, payment_intent, invoice)
"""

from __future__ import annotations

import logging
from typing import Any

_log = logging.getLogger(__name__)


def _get_stripe():
    """Importa e configura o cliente Stripe."""
    import stripe
    from ..config import get_settings
    s = get_settings()
    if not s.stripe_secret_key:
        raise RuntimeError("STRIPE_SECRET_KEY não configurado")
    stripe.api_key = s.stripe_secret_key
    return stripe


def create_checkout_session(
    family_id: str,
    plan_id: str,
    plan_code: str,
    stripe_price_id: str,
    success_url: str,
    cancel_url: str,
    customer_id: str | None = None,
    trial_days: int = 0,
) -> dict:
    """Cria uma Stripe Checkout Session para assinar um plano."""
    stripe = _get_stripe()

    params: dict[str, Any] = {
        "mode": "subscription",
        "line_items": [{"price": stripe_price_id, "quantity": 1}],
        "success_url": success_url,
        "cancel_url": cancel_url,
        "metadata": {"family_id": family_id, "plan_id": plan_id, "plan_code": plan_code},
        "allow_promotion_codes": True,
    }

    if customer_id:
        params["customer"] = customer_id
    if trial_days > 0:
        params["subscription_data"] = {"trial_period_days": trial_days}

    session = stripe.checkout.Session.create(**params)
    return {"session_id": session.id, "url": session.url}


def create_customer_portal_session(stripe_customer_id: str, return_url: str) -> str:
    """Cria uma sessão do portal de billing do cliente (gerenciar assinatura, invoices)."""
    stripe = _get_stripe()
    session = stripe.billing_portal.Session.create(
        customer=stripe_customer_id,
        return_url=return_url,
    )
    return session.url


async def handle_webhook_event(raw_body: bytes, signature: str) -> dict:
    """
    Valida a assinatura Stripe e processa o evento.
    Retorna {"handled": True/False, "event_type": ..., "error": ...}
    """
    stripe = _get_stripe()
    from ..config import get_settings
    webhook_secret = get_settings().stripe_webhook_secret

    try:
        event = stripe.Webhook.construct_event(raw_body, signature, webhook_secret)
    except stripe.error.SignatureVerificationError:
        _log.warning("stripe: assinatura inválida no webhook")
        return {"handled": False, "error": "invalid_signature"}

    event_type = event["type"]
    data = event["data"]["object"]

    _log.info("stripe: evento recebido → %s", event_type)

    try:
        if event_type == "customer.subscription.created":
            await _on_subscription_created(data)
        elif event_type == "customer.subscription.updated":
            await _on_subscription_updated(data)
        elif event_type == "customer.subscription.deleted":
            await _on_subscription_deleted(data)
        elif event_type == "invoice.payment_succeeded":
            await _on_invoice_paid(data)
        elif event_type == "invoice.payment_failed":
            await _on_invoice_failed(data)
        else:
            _log.debug("stripe: evento não tratado → %s", event_type)
            return {"handled": False, "event_type": event_type}
    except Exception:
        _log.exception("stripe: erro ao processar evento %s", event_type)
        return {"handled": False, "event_type": event_type, "error": "processing_error"}

    return {"handled": True, "event_type": event_type}


async def _get_pool():
    from ..db_postgres import get_async_pool
    from ..config import get_settings
    return await get_async_pool(get_settings().database_url)


async def _on_subscription_created(data: dict) -> None:
    family_id = data.get("metadata", {}).get("family_id")
    plan_id = data.get("metadata", {}).get("plan_id")
    if not family_id or not plan_id:
        _log.warning("stripe: subscription.created sem family_id/plan_id nos metadados")
        return

    pool = await _get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """INSERT INTO subscriptions
                   (family_id, plan_id, status, billing_period,
                    current_period_start, current_period_end,
                    stripe_subscription_id, stripe_customer_id)
                   VALUES (%s, %s, %s, %s,
                           TO_TIMESTAMP(%s), TO_TIMESTAMP(%s),
                           %s, %s)
                   ON CONFLICT (stripe_subscription_id) DO UPDATE
                   SET status = EXCLUDED.status, updated_at = NOW()""",
                (
                    family_id, plan_id,
                    _map_stripe_status(data.get("status", "active")),
                    "yearly" if data.get("items", {}).get("data", [{}])[0].get("plan", {}).get("interval") == "year" else "monthly",
                    data.get("current_period_start"),
                    data.get("current_period_end"),
                    data.get("id"),
                    data.get("customer"),
                ),
            )
    _log.info("stripe: assinatura criada para family %s", family_id)


async def _on_subscription_updated(data: dict) -> None:
    stripe_sub_id = data.get("id")
    if not stripe_sub_id:
        return

    pool = await _get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """UPDATE subscriptions
                   SET status = %s,
                       current_period_start = TO_TIMESTAMP(%s),
                       current_period_end = TO_TIMESTAMP(%s),
                       cancel_at_period_end = %s,
                       updated_at = NOW()
                   WHERE stripe_subscription_id = %s""",
                (
                    _map_stripe_status(data.get("status", "active")),
                    data.get("current_period_start"),
                    data.get("current_period_end"),
                    data.get("cancel_at_period_end", False),
                    stripe_sub_id,
                ),
            )


async def _on_subscription_deleted(data: dict) -> None:
    stripe_sub_id = data.get("id")
    if not stripe_sub_id:
        return

    pool = await _get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """UPDATE subscriptions
                   SET status = 'canceled', canceled_at = NOW(), updated_at = NOW()
                   WHERE stripe_subscription_id = %s""",
                (stripe_sub_id,),
            )
    _log.info("stripe: assinatura %s cancelada", stripe_sub_id)


async def _on_invoice_paid(data: dict) -> None:
    stripe_sub_id = data.get("subscription")
    pool = await _get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            # Busca subscription local
            await cur.execute(
                "SELECT id, family_id FROM subscriptions WHERE stripe_subscription_id = %s",
                (stripe_sub_id,),
            )
            sub_row = await cur.fetchone()
            if not sub_row:
                return

            sub_id, family_id = sub_row
            await cur.execute(
                """INSERT INTO payments
                   (subscription_id, family_id, amount_cents, currency, status,
                    stripe_invoice_id, stripe_payment_intent_id, paid_at)
                   VALUES (%s, %s, %s, %s, 'succeeded', %s, %s, NOW())
                   ON CONFLICT (stripe_invoice_id) DO NOTHING""",
                (
                    str(sub_id), str(family_id),
                    data.get("amount_paid", 0),
                    (data.get("currency") or "brl").upper(),
                    data.get("id"),
                    data.get("payment_intent"),
                ),
            )


async def _on_invoice_failed(data: dict) -> None:
    stripe_sub_id = data.get("subscription")
    pool = await _get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT id, family_id FROM subscriptions WHERE stripe_subscription_id = %s",
                (stripe_sub_id,),
            )
            sub_row = await cur.fetchone()
            if not sub_row:
                return

            sub_id, family_id = sub_row
            await cur.execute(
                """INSERT INTO payments
                   (subscription_id, family_id, amount_cents, currency, status, stripe_invoice_id)
                   VALUES (%s, %s, %s, %s, 'failed', %s)
                   ON CONFLICT (stripe_invoice_id) DO NOTHING""",
                (
                    str(sub_id), str(family_id),
                    data.get("amount_due", 0),
                    (data.get("currency") or "brl").upper(),
                    data.get("id"),
                ),
            )

    _log.warning("stripe: pagamento falhou para assinatura %s", stripe_sub_id)


def _map_stripe_status(stripe_status: str) -> str:
    mapping = {
        "trialing": "trialing",
        "active": "active",
        "past_due": "past_due",
        "canceled": "canceled",
        "unpaid": "past_due",
        "paused": "paused",
    }
    return mapping.get(stripe_status, "active")
