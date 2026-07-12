import asyncio
import hashlib
import random
import time

from app.core.database import session_context
from app.db.models import Category, Item, ItemSecret, ItemType, Prototype, Quest, Rarity

# Иерархия данных для связывания: Категория -> Типы -> Прототипы
HIERARCHY = {
    "Арт-объекты": {
        "color": "primary",
        "description": "Уличное искусство и необычные инсталляции",
        "types": {
            "Граффити": {
                "desc": "Современное стрит-арт искусство",
                "prototypes": ["Легендарное граффити", "Мурал на стене", "Стрит-арт портрет"]
            },
            "Инсталляция": {
                "desc": "Современные арт-объекты",
                "prototypes": ["Кинетическая скульптура", "Световая инсталляция", "Металлический дракон"]
            }
        }
    },
    "Историческое": {
        "color": "#FF9800",
        "description": "Старинные здания и памятники архитектуры",
        "types": {
            "Скульптура": {
                "desc": "Бронзовые и каменные статуи",
                "prototypes": ["Статуя поэта", "Бронзовый грифон", "Античный барельеф"]
            },
            "Архитектура": {
                "desc": "Уникальные элементы фасадов зданий",
                "prototypes": ["Резная дверь", "Старинные часы", "Лепнина на фасаде"]
            }
        }
    },
    "Тайники": {
        "color": "#9C27B0",
        "description": "Секретные локации, скрытые от глаз туристов",
        "types": {
            "Дворик": {
                "desc": "Скрытые колодцы и проходные дворы",
                "prototypes": ["Двор-колодец", "Проходной двор", "Тайный сквер"]
            },
            "Заброшенное": {
                "desc": "Старые заброшенные места",
                "prototypes": ["Забытый витраж", "Старая лестница", "Маяк на крыше"]
            }
        }
    },
    "Природа": {
        "color": "#4CAF50",
        "description": "Уютные зеленые зоны, скверы и аллеи",
        "types": {
            "Парк": {
                "desc": "Парки и скверы",
                "prototypes": ["Дерево желаний", "Аллея влюбленных", "Старый дуб"]
            },
            "Фонтан": {
                "desc": "Водные объекты",
                "prototypes": ["Фонтан желаний", "Каскадный фонтан", "Фонтан со львами"]
            }
        }
    }
}

QUESTS_DATA = [
    ("quest_shadows", "Тени Старого города", "1/5", 20, Rarity.RARE, 150),
    ("quest_artist", "Путь художника", "3/5", 60, Rarity.EPIC, 300),
    ("quest_secrets", "Тайны переулков", "0/4", 0, Rarity.COMMON, 100),
    ("quest_nature", "Зеленое сердце столицы", "2/3", 66, Rarity.COMMON, 200),
    ("quest_legends", "Городские легенды", "1/4", 25, Rarity.MYTHIC, 500)
]

SUFFIXES = [
    "на Тверской", "в переулке", "у метро", "на набережной", "в центре", 
    "на бульваре", "во дворе", "на крыше", "в парке", "у моста", 
    "на Арбате", "на Патриарших", "у Китай-города", "возле театра", "в тайном месте"
]

async def seed_db():
    async with session_context() as session:
        print("Creating quests...")
        db_quests = []
        for q_id, name, step, prog, rarity, xp in QUESTS_DATA:
            quest = Quest(
                id=q_id,
                name=name,
                step_label=step,
                progress_percent=prog,
                rarity=rarity,
                reward_xp=xp
            )
            session.add(quest)
            db_quests.append(quest)
        await session.flush()

        print("Building connected hierarchy (Categories -> Types -> Prototypes -> Items)...")
        created_secrets = []
        
        # Center of Moscow approx
        base_lat = 55.751244
        base_lon = 37.618423
        
        secret_counter = 1
        
        for cat_name, cat_data in HIERARCHY.items():
            # 1. Создаем Категорию
            cat = Category(title=cat_name, color=cat_data["color"], description=cat_data["description"])
            session.add(cat)
            await session.flush()
            
            for type_name, type_data in cat_data["types"].items():
                # 2. Создаем Тип
                t = ItemType(title=type_name, description=type_data["desc"])
                session.add(t)
                await session.flush()
                
                for proto_name in type_data["prototypes"]:
                    # 3. Создаем Прототип (жестко связанный с типом)
                    proto = Prototype(
                        title=proto_name,
                        type_id=t.id,
                        description=f"Базовый объект: {proto_name}",
                    )
                    session.add(proto)
                    await session.flush()
                    
                    # 4. Генерируем по 2 предмета и секрета на каждый прототип (итого ~44 точки)
                    for _ in range(2):
                        item_title = f"{proto_name} {random.choice(SUFFIXES)}"
                        item = Item(
                            title=item_title,
                            number=int(time.time() * 1000) % 1000000 + secret_counter,
                            prototype_id=proto.id,
                            category_id=cat.id,
                            type_id=t.id
                        )
                        session.add(item)
                        await session.flush()
                        
                        raw_secret = f"secret_token_{secret_counter:03d}"
                        secret_hash = hashlib.sha256(raw_secret.encode("utf-8")).hexdigest()
                        
                        # Для логики: связываем с квестом случайным образом, но сохраняем логику
                        assigned_quest = random.choice(db_quests) if random.random() > 0.4 else None
                        
                        secret_model = ItemSecret(
                            item_id=item.id,
                            secret_hash=secret_hash,
                            title=item_title,
                            category=cat.title,
                            rarity=random.choice(list(Rarity)),
                            latitude=base_lat + random.uniform(-0.03, 0.03),
                            longitude=base_lon + random.uniform(-0.03, 0.03),
                            reward_xp=random.randint(5, 50) * 10,
                            quest_id=assigned_quest.id if assigned_quest else None,
                            hidden=random.random() > 0.75,
                        )
                        session.add(secret_model)
                        created_secrets.append((item_title, raw_secret))
                        secret_counter += 1
                        
        await session.commit()
        
        print(f"\n=== SEED COMPLETED SUCCESSFULLY ({len(created_secrets)} items generated) ===")
        print("Generated Secrets (save these to test QR scanning):")
        for title, s in created_secrets:
            print(f" - {title[:30].ljust(32)} : {s}")
        print("====================================================\n")

if __name__ == "__main__":
    asyncio.run(seed_db())
