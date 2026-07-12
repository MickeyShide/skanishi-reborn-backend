from sqlalchemy import select
from fastapi import HTTPException
from app.db.models.shop import ShopItem, UserCosmetic, ShopItemType
from app.db.models.user import User
from app.services.business.base import BusinessService
from app.schemas.shop import ShopItemResponse

class ShopBusinessService(BusinessService):
    
    async def get_shop_items(self, user: User) -> list[ShopItemResponse]:
        # Get all active items
        items_result = await self._session.execute(
            select(ShopItem).where(ShopItem.is_active == True)
        )
        items = items_result.scalars().all()
        
        # Get user owned cosmetics
        owned_result = await self._session.execute(
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
                is_owned=is_owned,
                is_equipped=is_equipped,
            ))
            
        return response

    async def buy_item(self, user: User, item_id: int) -> ShopItemResponse:
        item = await self._session.get(ShopItem, item_id)
        if not item or not item.is_active:
            raise HTTPException(status_code=404, detail="Товар не найден")
            
        # Check if already owned
        existing = await self._session.execute(
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
        self._session.add(new_cosmetic)
        
        await self._session.flush()
        
        return ShopItemResponse(
            id=item.id,
            name=item.name,
            item_type=item.item_type,
            price=item.price,
            asset_url=item.asset_url,
            is_owned=True,
            is_equipped=False,
        )

    async def equip_item(self, user: User, item_id: int) -> ShopItemResponse:
        item = await self._session.get(ShopItem, item_id)
        if not item:
            raise HTTPException(status_code=404, detail="Товар не найден")
            
        # Verify ownership
        existing = await self._session.execute(
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
            
        await self._session.flush()
        
        return ShopItemResponse(
            id=item.id,
            name=item.name,
            item_type=item.item_type,
            price=item.price,
            asset_url=item.asset_url,
            is_owned=True,
            is_equipped=True,
        )
