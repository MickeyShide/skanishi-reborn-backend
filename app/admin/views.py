from sqladmin import ModelView
from app.db.models.user import User
from app.db.models.quest import Quest
from app.db.models.item_secrets import ItemSecret
from app.db.models.event import Event
from app.db.models.collection import Collection
from app.db.models.achievement import Achievement
from app.db.models.season import Season
from app.db.models.shop import ShopItem, UserCosmetic

class UserAdmin(ModelView, model=User):
    column_list = [User.id, User.tg_id, User.username, User.role, User.level, User.xp, User.is_private]
    column_searchable_list = [User.username, User.tg_id, User.first_name, User.last_name]
    column_sortable_list = [User.id, User.xp, User.level, User.rank]
    page_size = 50

class QuestAdmin(ModelView, model=Quest):
    column_list = [Quest.id, Quest.name, Quest.rarity, Quest.is_active, Quest.target_count]
    column_searchable_list = [Quest.name, Quest.step_label, Quest.condition_tag]
    column_sortable_list = [Quest.id, Quest.is_active]

class ItemSecretAdmin(ModelView, model=ItemSecret):
    column_list = [ItemSecret.id, ItemSecret.title, ItemSecret.rarity, ItemSecret.secret_hash, ItemSecret.is_active]
    column_searchable_list = [ItemSecret.title, ItemSecret.secret_hash, ItemSecret.description]

class EventAdmin(ModelView, model=Event):
    column_list = [Event.id, Event.title, Event.is_active, Event.starts_at, Event.ends_at]
    column_searchable_list = [Event.title]

class CollectionAdmin(ModelView, model=Collection):
    column_list = [Collection.id, Collection.name, Collection.reward_xp, Collection.is_active]
    column_searchable_list = [Collection.name, Collection.description]

class AchievementAdmin(ModelView, model=Achievement):
    column_list = [Achievement.id, Achievement.name, Achievement.rarity, Achievement.reward_xp]
    column_searchable_list = [Achievement.name, Achievement.description]

class SeasonAdmin(ModelView, model=Season):
    column_list = [Season.id, Season.name, Season.is_active, Season.starts_at, Season.ends_at]
    column_searchable_list = [Season.name]

class ShopItemAdmin(ModelView, model=ShopItem):
    column_list = [ShopItem.id, ShopItem.name, ShopItem.item_type, ShopItem.price, ShopItem.is_active]
    column_searchable_list = [ShopItem.name, ShopItem.item_type]

class UserCosmeticAdmin(ModelView, model=UserCosmetic):
    column_list = [UserCosmetic.id, UserCosmetic.user_id, UserCosmetic.shop_item_id]

admin_views = [
    UserAdmin,
    QuestAdmin,
    ItemSecretAdmin,
    EventAdmin,
    CollectionAdmin,
    AchievementAdmin,
    SeasonAdmin,
    ShopItemAdmin,
    UserCosmeticAdmin,
]
