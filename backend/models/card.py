# backend/app/models/card.py
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict, computed_field
from typing import Optional


# ============== Base Schemas ==============

class CardBase(BaseModel):
    """Base schema for a card entry"""
    card_id: str
    set_id: str
    card_number: int
    public_code: str
    card_name: str
    attr_energy: Optional[int] = None
    attr_power: Optional[int] = None
    attr_might: Optional[int] = None
    card_type: Optional[str] = None
    card_supertype: Optional[str] = None
    card_rarity: Optional[str] = None
    card_domain: list[str]
    card_image_url: Optional[str] = None
    card_artist: Optional[str] = None
    card_tags: list[str]
    alternate_art: bool = False
    overnumbered: bool = False
    signature: bool = False


class CardListResponse(BaseModel):
    cards: list[CardBase]
    total: Optional[int] = None
    page: Optional[int] = None
    limit: Optional[int] = None


class CardResponse(CardBase):
    text_rich: Optional[str] = None
    text_plain: Optional[str] = None
