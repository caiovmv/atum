"""Router de webhooks do Stripe — /api/webhooks/stripe (sem autenticação JWT)."""

from fastapi import APIRouter, HTTPException, Request, status

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post("/stripe")
async def stripe_webhook(request: Request) -> dict:
    """
    Recebe e processa eventos do Stripe.
    Valida a assinatura via Stripe-Signature header (HMAC-SHA256).
    """
    signature = request.headers.get("stripe-signature", "")
    if not signature:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Header Stripe-Signature ausente")

    raw_body = await request.body()

    from ..stripe_service import handle_webhook_event
    result = await handle_webhook_event(raw_body, signature)

    if result.get("error") == "invalid_signature":
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Assinatura inválida")

    return result


@router.post("/stripe/checkout/session")
async def create_checkout_session(
    request: Request,
) -> dict:
    """Cria sessão de checkout Stripe para assinar um plano."""
    from ..auth_service import get_current_user
    from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
    from fastapi import Depends

    body = await request.json()
    plan_stripe_price_id = body.get("stripe_price_id")
    success_url = body.get("success_url", "https://atum.loombeat.com/account?checkout=success")
    cancel_url = body.get("cancel_url", "https://atum.loombeat.com/account")

    if not plan_stripe_price_id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "stripe_price_id é obrigatório")

    # Extrai user do token manualmente (não usa Depends aqui para manter rota pública no prefixo)
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token não fornecido")

    import jwt as pyjwt
    from ...config import get_settings
    s = get_settings()
    try:
        payload = pyjwt.decode(auth[7:], s.jwt_secret, algorithms=["HS256"])
    except pyjwt.InvalidTokenError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token inválido")

    family_id = payload["family_id"]
    plan_id = body.get("plan_id", "")

    from ..stripe_service import create_checkout_session as _checkout
    return _checkout(
        family_id=family_id,
        plan_id=plan_id,
        plan_code=body.get("plan_code", ""),
        stripe_price_id=plan_stripe_price_id,
        success_url=success_url,
        cancel_url=cancel_url,
        trial_days=int(body.get("trial_days", 0)),
    )
