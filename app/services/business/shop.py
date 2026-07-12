from sqlalchemy import select
from fastapi import HTTPException
from app.db.models.shop import ShopItem, UserCosmetic, ShopItemType
from app.db.models.user import User
from app.services.business.base import BusinessService
from app.schemas.shop import ShopItemResponse

class ShopBusinessService(BusinessService):
    
    async def get_shop_items(self, user: User) -> list[ShopItemResponse]:
        session = await self._get_session()

        # Get all active items
        items_result = await session.execute(
            select(ShopItem).where(ShopItem.is_active.is_(True))
        )
        items = items_result.scalars().all()
        
        # Get user owned cosmetics
        owned_result = await session.execute(
            select(UserCosmetic.shop_item_id).where(UserCosmetic.user_id == user.id)
        )
        owned_ids = set(owned_result.scalars().all())
        
        response = []
        for item in items:
            is_owned = item.id in owned_ids
            is_equipped = False
            
            if item.item_type == ShopItemType.BORDER and user.active_border_id == item.id:
                is_equipped = True
            elif item.item_type == ShopItemType.BACKGROUND and user.active_bg_id == item.id:
                is_equipped = True
                
            response.append(ShopItemResponse(
                id=item.id,
                name=item.name,
                item_type=item.item_type,
                price=item.price,
                asset_url=item.asset_url,
                fragment_cost=item.fragment_cost,
                fragment_rarity=item.fragment_rarity,
                is_owned=is_owned,
                is_equipped=is_equipped,
            ))
            
        return response

    async def buy_item(self, user: User, item_id: int) -> ShopItemResponse:
        session = await self._get_session()

        item = await session.get(ShopItem, item_id)
        if not item or not item.is_active:
            raise HTTPException(status_code=404, detail="Товар не найден")
            
        # Check if already owned
        existing = await session.execute(
            select(UserCosmetic)
            .where(UserCosmetic.user_id == user.id, UserCosmetic.shop_item_id == item_id)
        )
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Товар уже куплен")
            
        if user.coins < item.price:
            raise HTTPException(status_code=400, detail="Недостаточно монет")
            
        # Deduct coins and add to inventory
        user.coins -= item.price
        new_cosmetic = UserCosmetic(user_id=user.id, shop_item_id=item_id)
        session.add(new_cosmetic)
        
        await session.flush()
        
        return ShopItemResponse(
            id=item.id,
            name=item.name,
            item_type=item.item_type,
            price=item.price,
            asset_url=item.asset_url,
            fragment_cost=item.fragment_cost,
            fragment_rarity=item.fragment_rarity,
            is_owned=True,
            is_equipped=False,
        )

    async def craft_item(self, user: User, item_id: int) -> ShopItemResponse:
        session = await self._get_session()

        item = await session.get(ShopItem, item_id)
        if not item or not item.is_active:
            raise HTTPException(status_code=404, detail="Товар не найден")
            
        if not item.fragment_cost or not item.fragment_rarity:
            raise HTTPException(status_code=400, detail="Этот товар нельзя скрафтить")
            
        existing = await session.execute(
            select(UserCosmetic)
            .where(UserCosmetic.user_id == user.id, UserCosmetic.shop_item_id == item_id)
        )
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Товар уже куплен")
            
        frag_attr = f"fragments_{item.fragment_rarity.lower()}"
        if not hasattr(user, frag_attr):
            raise HTTPException(status_code=400, detail="Неверная редкость осколков")
            
        current_fragments = getattr(user, frag_attr)
        if current_fragments < item.fragment_cost:
            raise HTTPException(status_code=400, detail="Недостаточно осколков")
            
        setattr(user, frag_attr, current_fragments - item.fragment_cost)
        
        new_cosmetic = UserCosmetic(user_id=user.id, shop_item_id=item_id)
        session.add(new_cosmetic)
        
        await session.flush()
        
        return ShopItemResponse(
            id=item.id,
            name=item.name,
            item_type=item.item_type,
            price=item.price,
            asset_url=item.asset_url,
            fragment_cost=item.fragment_cost,
            fragment_rarity=item.fragment_rarity,
            is_owned=True,
            is_equipped=False,
        )

    async def equip_item(self, user: User, item_id: int) -> ShopItemResponse:
        session = await self._get_session()

        item = await session.get(ShopItem, item_id)
        if not item:
            raise HTTPException(status_code=404, detail="Товар не найден")
            
        # Verify ownership
        existing = await session.execute(
            select(UserCosmetic)
            .where(UserCosmetic.user_id == user.id, UserCosmetic.shop_item_id == item_id)
        )
        if not existing.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Товар не куплен")
            
        # Equip
        if item.item_type == ShopItemType.BORDER:
            user.active_border_id = item.id
        elif item.item_type == ShopItemType.BACKGROUND:
            user.active_bg_id = item.id
            
        await session.flush()
        
        return ShopItemResponse(
            id=item.id,
            name=item.name,
            item_type=item.item_type,
            price=item.price,
            asset_url=item.asset_url,
            fragment_cost=item.fragment_cost,
            fragment_rarity=item.fragment_rarity,
            is_owned=True,
            is_equipped=True,
        )
