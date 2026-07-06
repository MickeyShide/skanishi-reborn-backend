import asyncio
import hashlib
import random
import string
import time

from app.core.database import session_context
from app.db.models import (
    Category, ItemType, Prototype, Item, ItemSecret, MapPoint, Quest, Rarity
)

def random_string(length=10):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

async def seed_db():
    async with session_context() as session:
        print("Creating categories...")
        cat1 = Category(title=f"Cat_{random_string(4)}", color="#ff0000", description="Desc 1")
        cat2 = Category(title=f"Cat_{random_string(4)}", color="primary", description="Desc 2")
        session.add_all([cat1, cat2])
        await session.flush()
        
        print("Creating item types...")
        type1 = ItemType(title=f"Type_{random_string(4)}", description="Type 1")
        session.add(type1)
        await session.flush()
        
        print("Creating prototypes...")
        proto1 = Prototype(title=f"Proto_{random_string(4)}", type_id=type1.id, description="Proto 1")
        session.add(proto1)
        await session.flush()
        
        print("Creating quests...")
        quest1 = Quest(
            id=f"quest_{random_string(6)}",
            name=f"Quest {random_string(4)}",
            step_label="1/3",
            progress_percent=33,
            rarity=Rarity.COMMON,
            reward_xp=100
        )
        session.add(quest1)
        await session.flush()
        
        print("Creating map points...")
        for i in range(10):
            pt = MapPoint(
                id=f"pt_{random_string(6)}",
                name=f"Point {random_string(4)}",
                category=cat1.title,
                rarity=random.choice(list(Rarity)),
                latitude=55.751244 + random.uniform(-0.01, 0.01),
                longitude=37.618423 + random.uniform(-0.01, 0.01),
                reward_xp=50,
                quest_id=quest1.id if i % 3 == 0 else None
            )
            session.add(pt)
        await session.flush()
        
        print("Creating items and secrets...")
        created_secrets = []
        for i in range(5):
            item = Item(
                title=f"Item {random_string(4)}",
                number=int(time.time() * 1000) % 1000000 + i,
                prototype_id=proto1.id,
                category_id=cat1.id,
                type_id=type1.id
            )
            session.add(item)
            await session.flush()
            
            raw_secret = f"secret_{random_string(8)}"
            secret_hash = hashlib.sha256(raw_secret.encode("utf-8")).hexdigest()
            
            secret_model = ItemSecret(
                item_id=item.id,
                secret_hash=secret_hash,
                title=f"Secret for {item.title}"
            )
            session.add(secret_model)
            created_secrets.append(raw_secret)
            
        await session.commit()
        
        print("\n=== SEED COMPLETED SUCCESSFULLY ===")
        print("Generated Secrets (save these to test QR scanning):")
        for s in created_secrets:
            print(f" - {s}")
        print("===================================\n")

if __name__ == "__main__":
    asyncio.run(seed_db())
