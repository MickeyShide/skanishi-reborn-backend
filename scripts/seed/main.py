"""Idempotent seed data for Skanishi.

Usage:
    python -m scripts.seed.main --mode minimal
    python -m scripts.seed.main --mode demo
    python -m scripts.seed.main --mode large
    python -m scripts.seed.main --mode demo --reset

Modes:
    minimal  - system data only (achievements, quests, types).
               Safe to run in production.
    demo     - full demo content + 5 test users.
               NEVER run in production.
    large    - 100 items, 50 secrets, 20 test users.
               Development only.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import random
import string
import sys
from pathlib import Path

# Allow running as a module from the backend directory
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.config import settings, Environment
from app.core.database import session_context
from app.db.models import (
    Achievement,
    Category,
    Collection,
    CollectionItem,
    Event,
    Item,
    ItemSecret,
    ItemType,
    Prototype,
    Quest,
    Rarity,
    ShopItem,
)
from app.db.models.achievement_condition import AchievementCondition, AchievementConditionType
from app.db.models.shop import ShopItemType


def sha256_secret(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


def rand_str(n: int = 8) -> str:
    return "".join(random.choices(string.ascii_lowercase + string.digits, k=n))


async def get_or_create(session, model, **kwargs):
    """Create model instance if it doesn't exist (keyed by 'id' or first kwarg)."""
    from sqlalchemy import select

    pk_field = "id"
    pk_val = kwargs.get(pk_field)
    if pk_val:
        existing = await session.get(model, pk_val)
        if existing:
            return existing, False

    obj = model(**kwargs)
    session.add(obj)
    await session.flush()
    await session.refresh(obj)
    return obj, True


# ──────────────────────────────────────────────────────────────────────────────
# SYSTEM DATA — safe in all environments
# ──────────────────────────────────────────────────────────────────────────────

ITEM_TYPES = [
    {"id": "type-token", "title": "Жетоны", "description": "Маленькие металлические диски с символами"},
    {"id": "type-fragment", "title": "Фрагменты", "description": "Осколки, части, кусочки артефактов"},
    {"id": "type-card", "title": "Карточки", "description": "Ламинированные карточки с историей"},
    {"id": "type-badge", "title": "Значки", "description": "Коллекционные значки"},
]

CATEGORIES = [
    {"id": "urban-artifacts", "title": "Артефакты города", "color": "#6B8CFF", "description": "Предметы с историей городских пространств"},
    {"id": "transit-relics", "title": "Реликвии транзита", "color": "#4ECDC4", "description": "Предметы транспортной инфраструктуры"},
    {"id": "street-culture", "title": "Уличная культура", "color": "#FF6B6B", "description": "Предметы уличного искусства и субкультур"},
    {"id": "industrial-age", "title": "Индустриальная эпоха", "color": "#FFA500", "description": "Предметы заводского прошлого"},
]

QUESTS = [
    {
        "id": "first-scan",
        "name": "Первое открытие",
        "step_label": "0/1",
        "progress_percent": 0,
        "rarity": Rarity.COMMON,
        "reward_xp": 100,
        "target_count": 1,
        "condition_tag": None,
    },
    {
        "id": "metro-explorer",
        "name": "Исследователь метро",
        "step_label": "0/3",
        "progress_percent": 0,
        "rarity": Rarity.RARE,
        "reward_xp": 300,
        "target_count": 3,
        "condition_tag": None,
    },
    {
        "id": "urban-legend",
        "name": "Городская легенда",
        "step_label": "0/10",
        "progress_percent": 0,
        "rarity": Rarity.EPIC,
        "reward_xp": 750,
        "target_count": 10,
        "condition_tag": None,
    },
    {
        "id": "night-owl",
        "name": "Ночная сова",
        "step_label": "0/3",
        "progress_percent": 0,
        "rarity": Rarity.RARE,
        "reward_xp": 500,
        "target_count": 3,
        "condition_tag": "night-scan",
    },
]

ACHIEVEMENTS = [
    {
        "id": "first-scan",
        "icon": "qr",
        "name": "Первопроходец",
        "rarity": Rarity.COMMON,
        "description": "Отсканируй первую метку",
        "reward_xp": 50,
        "conditions": [{"type": AchievementConditionType.SCAN_COUNT, "threshold": 1}],
    },
    {
        "id": "explorer-5",
        "icon": "map",
        "name": "Исследователь",
        "rarity": Rarity.COMMON,
        "description": "Отсканируй 5 меток",
        "reward_xp": 100,
        "conditions": [{"type": AchievementConditionType.SCAN_COUNT, "threshold": 5}],
    },
    {
        "id": "explorer-25",
        "icon": "star",
        "name": "Опытный следопыт",
        "rarity": Rarity.RARE,
        "description": "Отсканируй 25 меток",
        "reward_xp": 300,
        "conditions": [{"type": AchievementConditionType.SCAN_COUNT, "threshold": 25}],
    },
    {
        "id": "level-5",
        "icon": "bolt",
        "name": "Пятый уровень",
        "rarity": Rarity.RARE,
        "description": "Достигни 5 уровня",
        "reward_xp": 200,
        "conditions": [{"type": AchievementConditionType.LEVEL_REACHED, "threshold": 5}],
    },
    {
        "id": "streak-7",
        "icon": "fire",
        "name": "Неделя исследований",
        "rarity": Rarity.EPIC,
        "description": "7 дней подряд в приложении",
        "reward_xp": 400,
        "conditions": [{"type": AchievementConditionType.STREAK_DAYS, "threshold": 7}],
    },
    {
        "id": "quest-master",
        "icon": "trophy",
        "name": "Мастер квестов",
        "rarity": Rarity.EPIC,
        "description": "Завершить 3 квеста",
        "reward_xp": 500,
        "conditions": [{"type": AchievementConditionType.QUEST_COUNT, "threshold": 3}],
    },
]


async def seed_system(session) -> None:
    """Seed item types, categories, quests, achievements."""
    print("-> Seeding item types...")
    for data in ITEM_TYPES:
        from sqlalchemy import select
        existing = (await session.execute(
            select(ItemType).where(ItemType.title == data["title"])
        )).scalar_one_or_none()
        if not existing:
            obj = ItemType(title=data["title"], description=data["description"])
            session.add(obj)
    await session.flush()

    print("-> Seeding categories...")
    for data in CATEGORIES:
        from sqlalchemy import select
        existing = (await session.execute(
            select(Category).where(Category.title == data["title"])
        )).scalar_one_or_none()
        if not existing:
            obj = Category(title=data["title"], color=data["color"], description=data["description"])
            session.add(obj)
    await session.flush()

    print("-> Seeding quests...")
    for data in QUESTS:
        existing = await session.get(Quest, data["id"])
        if not existing:
            obj = Quest(**{k: v for k, v in data.items()})
            session.add(obj)
    await session.flush()

    print("-> Seeding achievements + conditions...")
    for data in ACHIEVEMENTS:
        conditions = data.pop("conditions", [])
        existing = await session.get(Achievement, data["id"])
        if not existing:
            obj = Achievement(**data)
            session.add(obj)
            await session.flush()
            await session.refresh(obj)
            for cond in conditions:
                session.add(AchievementCondition(
                    achievement_id=obj.id,
                    condition_type=cond["type"],
                    threshold=cond["threshold"],
                ))
        data["conditions"] = conditions  # restore for potential re-use
    await session.flush()


# ──────────────────────────────────────────────────────────────────────────────
# DEMO DATA — development only
# ──────────────────────────────────────────────────────────────────────────────

METRO_ITEMS = [
    {"slug": "metro-token-1935", "title": "Жетон образца 1935", "number": 1001, "rarity": Rarity.RARE},
    {"slug": "metro-token-1961", "title": "Жетон опытный 1961", "number": 1002, "rarity": Rarity.EPIC},
    {"slug": "metro-token-1985", "title": "Жетон юбилейный 1985", "number": 1003, "rarity": Rarity.RARE},
    {"slug": "metro-token-1992", "title": "Жетон экспериментальный 1992", "number": 1004, "rarity": Rarity.LEGENDARY},
    {"slug": "metro-token-2002", "title": "Жетон последний 2002", "number": 1005, "rarity": Rarity.EPIC},
]

STREET_ART_ITEMS = [
    {"slug": "street-mural-fragment", "title": "Фрагмент мурала «Крылья»", "number": 2001, "rarity": Rarity.COMMON},
    {"slug": "street-stencil-card", "title": "Трафаретная карточка", "number": 2002, "rarity": Rarity.RARE},
    {"slug": "street-spray-can", "title": "Баллончик с краской", "number": 2003, "rarity": Rarity.EPIC},
    {"slug": "street-sketchbook", "title": "Скетч-блокнот", "number": 2004, "rarity": Rarity.LEGENDARY},
]

INDUSTRIAL_ITEMS = [
    {"slug": "factory-badge-zil", "title": "Значок ЗИЛ", "number": 3001, "rarity": Rarity.COMMON},
    {"slug": "factory-pass-red-october", "title": "Пропуск «Красный Октябрь»", "number": 3002, "rarity": Rarity.RARE},
    {"slug": "workshop-plate-taganka", "title": "Табличка цеха Таганки", "number": 3003, "rarity": Rarity.RARE},
    {"slug": "signal-lamp-dynamo", "title": "Сигнальная лампа «Динамо»", "number": 3004, "rarity": Rarity.EPIC},
    {"slug": "engineer-notebook-azlk", "title": "Блокнот инженера АЗЛК", "number": 3005, "rarity": Rarity.LEGENDARY},
]

SHOP_ITEMS = [
    {"name": "Неоновый контур", "item_type": ShopItemType.BORDER, "price": 120, "asset_url": "/assets/shop/borders/neon-frame.png"},
    {"name": "Индустриальная рамка", "item_type": ShopItemType.BORDER, "price": 180, "asset_url": "/assets/shop/borders/industrial-frame.png"},
    {"name": "Пиксельный обвод", "item_type": ShopItemType.BORDER, "price": 250, "asset_url": "/assets/shop/borders/pixel-frame.png"},
    {"name": "Ночной город", "item_type": ShopItemType.BACKGROUND, "price": 200, "asset_url": "/assets/shop/backgrounds/night-city.jpg"},
    {"name": "Карта метро", "item_type": ShopItemType.BACKGROUND, "price": 280, "asset_url": "/assets/shop/backgrounds/metro-map.jpg"},
    {"name": "Заводской бетон", "item_type": ShopItemType.BACKGROUND, "price": 320, "asset_url": "/assets/shop/backgrounds/factory-wall.jpg"},
    {"name": "Первопроходец", "item_type": ShopItemType.TITLE, "price": 90, "asset_url": "/assets/shop/titles/pathfinder.svg"},
    {"name": "Охотник за метками", "item_type": ShopItemType.TITLE, "price": 150, "asset_url": "/assets/shop/titles/hunter.svg"},
    {"name": "Легенда района", "item_type": ShopItemType.TITLE, "price": 220, "asset_url": "/assets/shop/titles/legend.svg"},
]


async def seed_demo(session) -> None:
    """Seed demo content: items, secrets, collections, events."""
    print("-> Seeding demo items...")

    # Get first type and transit category
    from sqlalchemy import select, text

    async def add_collection_items(collection_id: str, item_ids: list[int]) -> None:
        for item_id in item_ids:
            await session.execute(
                text(
                    """
                    INSERT INTO collection_items (collection_id, item_id)
                    VALUES (:collection_id, :item_id)
                    ON CONFLICT (collection_id, item_id) DO NOTHING
                    """
                ),
                {"collection_id": collection_id, "item_id": item_id},
            )
    transit_type = (await session.execute(
        select(ItemType).where(ItemType.title == "Жетоны")
    )).scalar_one_or_none()
    street_type = (await session.execute(
        select(ItemType).where(ItemType.title == "Фрагменты")
    )).scalar_one_or_none()
    transit_cat = (await session.execute(
        select(Category).where(Category.title == "Реликвии транзита")
    )).scalar_one_or_none()
    street_cat = (await session.execute(
        select(Category).where(Category.title == "Уличная культура")
    )).scalar_one_or_none()
    industrial_type = (await session.execute(
        select(ItemType).where(ItemType.title == "Значки")
    )).scalar_one_or_none()
    industrial_cat = (await session.execute(
        select(Category).where(Category.title == "Индустриальная эпоха")
    )).scalar_one_or_none()

    # Need prototypes
    metro_proto_existing = (await session.execute(
        select(Prototype).where(Prototype.title == "Прототип: Жетоны метро")
    )).scalar_one_or_none()
    if not metro_proto_existing:
        metro_proto = Prototype(title="Прототип: Жетоны метро", type_id=transit_type.id if transit_type else 1, description="Жетоны московского метро разных эпох")
        session.add(metro_proto)
        await session.flush()
        await session.refresh(metro_proto)
    else:
        metro_proto = metro_proto_existing

    street_proto_existing = (await session.execute(
        select(Prototype).where(Prototype.title == "Прототип: Стрит-арт")
    )).scalar_one_or_none()
    if not street_proto_existing:
        street_proto = Prototype(title="Прототип: Стрит-арт", type_id=street_type.id if street_type else 1, description="Предметы уличной культуры")
        session.add(street_proto)
        await session.flush()
        await session.refresh(street_proto)
    else:
        street_proto = street_proto_existing

    industrial_proto_existing = (await session.execute(
        select(Prototype).where(Prototype.title == "Прототип: Индустриальные реликвии")
    )).scalar_one_or_none()
    if not industrial_proto_existing:
        industrial_proto = Prototype(
            title="Прототип: Индустриальные реликвии",
            type_id=industrial_type.id if industrial_type else 1,
            description="Предметы заводской эпохи и промышленных районов",
        )
        session.add(industrial_proto)
        await session.flush()
        await session.refresh(industrial_proto)
    else:
        industrial_proto = industrial_proto_existing

    metro_item_ids = []
    for data in METRO_ITEMS:
        existing = (await session.execute(
            select(Item).where(Item.number == data["number"])
        )).scalar_one_or_none()
        if not existing:
            item = Item(
                title=data["title"],
                number=data["number"],
                prototype_id=metro_proto.id,
                category_id=transit_cat.id if transit_cat else 1,
                type_id=transit_type.id if transit_type else 1,
            )
            session.add(item)
            await session.flush()
            await session.refresh(item)
        else:
            item = existing
        metro_item_ids.append(item.id)

        # Create QR secret for this item
        raw_secret = f"demo-metro-{data['slug']}"
        secret_hash = sha256_secret(raw_secret)
        existing_secret = (await session.execute(
            select(ItemSecret).where(ItemSecret.secret_hash == secret_hash)
        )).scalar_one_or_none()
        if not existing_secret:
            session.add(ItemSecret(
                item_id=item.id,
                secret_hash=secret_hash,
                title=data["title"],
                category="Реликвии транзита",
                rarity=data["rarity"],
                latitude=55.751244 + random.uniform(-0.05, 0.05),
                longitude=37.618423 + random.uniform(-0.05, 0.05),
                reward_xp=100 if data["rarity"] == Rarity.COMMON else 200 if data["rarity"] == Rarity.RARE else 350,
                quest_id="metro-explorer",
                description="Спрятан рядом с транспортным узлом, ищите старые схемы, турникеты и детали навигации.",
                is_big=data["rarity"] in {Rarity.EPIC, Rarity.LEGENDARY},
                has_hint=True,
                hidden=False,
            ))
    await session.flush()

    street_item_ids = []
    for data in STREET_ART_ITEMS:
        existing = (await session.execute(
            select(Item).where(Item.number == data["number"])
        )).scalar_one_or_none()
        if not existing:
            item = Item(
                title=data["title"],
                number=data["number"],
                prototype_id=street_proto.id,
                category_id=street_cat.id if street_cat else 1,
                type_id=street_type.id if street_type else 1,
            )
            session.add(item)
            await session.flush()
            await session.refresh(item)
        else:
            item = existing
        street_item_ids.append(item.id)

        raw_secret = f"demo-street-{data['slug']}"
        secret_hash = sha256_secret(raw_secret)
        existing_secret = (await session.execute(
            select(ItemSecret).where(ItemSecret.secret_hash == secret_hash)
        )).scalar_one_or_none()
        if not existing_secret:
            session.add(ItemSecret(
                item_id=item.id,
                secret_hash=secret_hash,
                title=data["title"],
                category="Уличная культура",
                rarity=data["rarity"],
                latitude=55.761244 + random.uniform(-0.05, 0.05),
                longitude=37.638423 + random.uniform(-0.05, 0.05),
                reward_xp=50 if data["rarity"] == Rarity.COMMON else 150 if data["rarity"] == Rarity.RARE else 300,
                description="Ищите во дворах, под арками и рядом с локальными арт-точками.",
                is_big=data["rarity"] == Rarity.LEGENDARY,
                has_hint=data["rarity"] != Rarity.COMMON,
                hidden=False,
            ))
    await session.flush()

    industrial_item_ids = []
    for index, data in enumerate(INDUSTRIAL_ITEMS):
        existing = (await session.execute(
            select(Item).where(Item.number == data["number"])
        )).scalar_one_or_none()
        if not existing:
            item = Item(
                title=data["title"],
                number=data["number"],
                prototype_id=industrial_proto.id,
                category_id=industrial_cat.id if industrial_cat else 1,
                type_id=industrial_type.id if industrial_type else 1,
            )
            session.add(item)
            await session.flush()
            await session.refresh(item)
        else:
            item = existing
        industrial_item_ids.append(item.id)

        raw_secret = f"demo-industrial-{data['slug']}"
        secret_hash = sha256_secret(raw_secret)
        existing_secret = (await session.execute(
            select(ItemSecret).where(ItemSecret.secret_hash == secret_hash)
        )).scalar_one_or_none()
        if not existing_secret:
            session.add(ItemSecret(
                item_id=item.id,
                secret_hash=secret_hash,
                title=data["title"],
                category="Индустриальная эпоха",
                rarity=data["rarity"],
                latitude=55.731244 + random.uniform(-0.07, 0.07),
                longitude=37.588423 + random.uniform(-0.07, 0.07),
                reward_xp=90 if data["rarity"] == Rarity.COMMON else 180 if data["rarity"] == Rarity.RARE else 320 if data["rarity"] == Rarity.EPIC else 500,
                quest_id="urban-legend" if index % 2 == 0 else "night-owl",
                description="Обычно такие находки прячутся у старых корпусов, проходных и бывших производственных линий.",
                is_big=data["rarity"] in {Rarity.EPIC, Rarity.LEGENDARY},
                has_hint=True,
                hidden=index % 2 == 1,
            ))
    await session.flush()

    print("-> Seeding collections...")
    metro_col = await session.get(Collection, "metro-tokens")
    if not metro_col:
        metro_col = Collection(
            id="metro-tokens",
            name="Потерянные жетоны метро",
            description="Соберите все жетоны московского метро разных эпох",
            reward_xp=500,
        )
        session.add(metro_col)
        await session.flush()
        await add_collection_items("metro-tokens", metro_item_ids)

    street_col = await session.get(Collection, "street-art-set")
    if not street_col:
        street_col = Collection(
            id="street-art-set",
            name="Граффити квартала",
            description="Артефакты уличного искусства района",
            reward_xp=400,
        )
        session.add(street_col)
        await session.flush()
        await add_collection_items("street-art-set", street_item_ids)

    industrial_col = await session.get(Collection, "factory-echoes")
    if not industrial_col:
        industrial_col = Collection(
            id="factory-echoes",
            name="Эхо заводов",
            description="Соберите артефакты индустриального прошлого города",
            reward_xp=650,
        )
        session.add(industrial_col)
        await session.flush()
        await add_collection_items("factory-echoes", industrial_item_ids)

    await session.flush()

    print("-> Seeding demo events...")
    from datetime import UTC, datetime, timedelta
    from decimal import Decimal

    now = datetime.now(UTC)
    demo_events = [
        {
            "id": "double-xp-weekend",
            "title": "Выходные двойного XP",
            "rarity": Rarity.RARE,
            "xp_multiplier": Decimal("2.0"),
            "starts_at": now - timedelta(hours=1),
            "ends_at": now + timedelta(days=2),
            "is_active": True,
        },
        {
            "id": "night-hunt",
            "title": "Ночная охота за артефактами",
            "rarity": Rarity.EPIC,
            "xp_multiplier": Decimal("2.5"),
            "starts_at": now + timedelta(hours=6),
            "ends_at": now + timedelta(days=3),
            "is_active": True,
        },
        {
            "id": "district-rush",
            "title": "Рывок по району",
            "rarity": Rarity.COMMON,
            "xp_multiplier": Decimal("1.5"),
            "starts_at": now - timedelta(days=1),
            "ends_at": now + timedelta(days=1),
            "is_active": True,
        },
    ]
    for event_data in demo_events:
        demo_event = await session.get(Event, event_data["id"])
        if not demo_event:
            session.add(Event(**event_data))
    await session.flush()

    print("-> Seeding shop cosmetics...")
    for data in SHOP_ITEMS:
        existing = (await session.execute(
            select(ShopItem).where(ShopItem.name == data["name"])
        )).scalar_one_or_none()
        if not existing:
            session.add(ShopItem(**data))
    await session.flush()

    print(f"\n{'='*50}")
    print("DEMO SEED SECRETS (use these to test QR scanning):")
    for data in METRO_ITEMS:
        print(f"  Metro: demo-metro-{data['slug']}")
    for data in STREET_ART_ITEMS:
        print(f"  Street: demo-street-{data['slug']}")
    for data in INDUSTRIAL_ITEMS:
        print(f"  Industrial: demo-industrial-{data['slug']}")
    print("="*50)


# ──────────────────────────────────────────────────────────────────────────────
# Entry point
# ──────────────────────────────────────────────────────────────────────────────

async def main(mode: str, reset: bool) -> None:
    if mode == "demo" and settings.APP_ENV == Environment.PROD:
        print("ERROR: demo mode is not allowed in production!")
        sys.exit(1)

    async with session_context() as session:
        if mode in ("minimal", "demo", "large"):
            await seed_system(session)

        if mode in ("demo", "large"):
            await seed_demo(session)

        await session.commit()

    print(f"\n[ok] Seed [{mode}] completed successfully.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Skanishi seed script")
    parser.add_argument(
        "--mode",
        choices=["minimal", "demo", "large"],
        default="minimal",
        help="Seed mode",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Reset demo data before seeding (not yet implemented)",
    )
    args = parser.parse_args()
    asyncio.run(main(args.mode, args.reset))
