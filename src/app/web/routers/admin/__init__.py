"""Routers de backoffice — requerem backoffice_role via JWT."""

from fastapi import APIRouter

from . import financial, invites, plans, promo_codes, settings, storage, subscriptions, users

router = APIRouter(prefix="/admin", tags=["backoffice"])

router.include_router(users.router)
router.include_router(plans.router)
router.include_router(subscriptions.router)
router.include_router(financial.router)
router.include_router(invites.router)
router.include_router(promo_codes.router)
router.include_router(settings.router)
router.include_router(storage.router)
