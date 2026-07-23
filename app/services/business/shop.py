from app.db.models.shop import ShopItemType
from app.db.models.user import User
from app.services.business.base import BusinessService
from app.schemas.shop import ShopItemResponse
from app.services.errors import (
    InsufficientCoinsError,
    InsufficientFragmentsError,
    InvalidFragmentRarityError,
    ItemNotCraftableError,
    ShopItemAlreadyOwnedError,
    ShopItemNotFoundError,
    ShopItemNotOwnedError,
)
from app.services.shop import ShopService
from app.services.user import UserService

class ShopBusinessService(BusinessService):
    shop_service: ShopService
    user_service: UserService

    async def get_shop_items(self, user: User) -> list[ShopItemResponse]:
        items = await self.shop_service.get_active_items()
        owned_ids = await self.shop_service.get_owned_item_ids(
            user_id=user.id
        )

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
        item = await self.shop_service.get_active_item(item_id)
        if item is None:
            raise ShopItemNotFoundError()

        if await self.shop_service.is_owned(user_id=user.id, item_id=item_id):
            raise ShopItemAlreadyOwnedError()

        if user.coins < item.price:
            raise InsufficientCoinsError()

        await self.user_service.update_fields(user, coins=user.coins - item.price)
        await self.shop_service.grant_item(user_id=user.id, item_id=item_id)

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
        item = await self.shop_service.get_active_item(item_id)
        if item is None:
            raise ShopItemNotFoundError()
            
        if not item.fragment_cost or not item.fragment_rarity:
            raise ItemNotCraftableError()
            
        if await self.shop_service.is_owned(user_id=user.id, item_id=item_id):
            raise ShopItemAlreadyOwnedError()
            
        frag_attr = f"fragments_{item.fragment_rarity.lower()}"
        if not hasattr(user, frag_attr):
            raise InvalidFragmentRarityError()
            
        current_fragments = getattr(user, frag_attr)
        if current_fragments < item.fragment_cost:
            raise InsufficientFragmentsError()
            
        await self.user_service.update_fields(
            user,
            **{frag_attr: current_fragments - item.fragment_cost},
        )
        await self.shop_service.grant_item(user_id=user.id, item_id=item_id)

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
        item = await self.shop_service.get_item(item_id)
        if item is None:
            raise ShopItemNotFoundError()

        if not await self.shop_service.is_owned(user_id=user.id, item_id=item_id):
            raise ShopItemNotOwnedError()

        if item.item_type == ShopItemType.BORDER:
            await self.user_service.update_fields(user, active_border_id=item.id)
        elif item.item_type == ShopItemType.BACKGROUND:
            await self.user_service.update_fields(user, active_bg_id=item.id)

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
