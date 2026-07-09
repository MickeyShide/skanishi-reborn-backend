import asyncio
import os
import sys
from pathlib import Path
from sqlalchemy import select

# Add backend dir to sys.path
sys.path.append(str(Path(__file__).parent.parent))

from app.core.database import session_context
from app.db.models.item import ItemSecret

HTML_TEMPLATE = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Skanishi QR Codes</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/qrcodejs/1.0.0/qrcode.min.js"></script>
<style>
    body { font-family: sans-serif; background: #fff; color: #000; padding: 20px; }
    .grid { display: flex; flex-wrap: wrap; gap: 20px; }
    .card { border: 1px dashed #ccc; padding: 20px; width: 220px; text-align: center; page-break-inside: avoid; }
    .qr { margin: 0 auto 10px; width: 128px; height: 128px; }
    .title { font-weight: bold; font-size: 16px; margin-bottom: 5px; }
    .rarity { font-size: 12px; color: #666; margin-bottom: 5px; text-transform: uppercase; }
    .id { font-family: monospace; font-size: 10px; color: #999; }
</style>
</head>
<body>
    <h1>Skanishi QR Codes</h1>
    <div class="grid" id="grid"></div>

    <script>
        const secrets = {secrets_json};
        const baseUrl = "https://t.me/skanishi_bot/app?startapp=";

        const grid = document.getElementById("grid");

        secrets.forEach(s => {
            const card = document.createElement("div");
            card.className = "card";

            const qrDiv = document.createElement("div");
            qrDiv.className = "qr";

            const title = document.createElement("div");
            title.className = "title";
            title.textContent = s.title;

            const rarity = document.createElement("div");
            rarity.className = "rarity";
            rarity.textContent = s.rarity;

            const idStr = document.createElement("div");
            idStr.className = "id";
            idStr.textContent = s.secret;

            card.appendChild(qrDiv);
            card.appendChild(title);
            card.appendChild(rarity);
            card.appendChild(idStr);
            grid.appendChild(card);

            new QRCode(qrDiv, {
                text: baseUrl + s.secret,
                width: 128,
                height: 128,
                colorDark : "#000000",
                colorLight : "#ffffff",
                correctLevel : QRCode.CorrectLevel.H
            });
        });
    </script>
</body>
</html>
"""

async def export_qrs():
    print("Exporting QR codes...")
    async with session_context() as session:
        result = await session.execute(select(ItemSecret).order_by(ItemSecret.title))
        secrets = list(result.scalars().all())

    secrets_data = [
        {
            "title": s.title,
            "rarity": s.rarity.value if hasattr(s.rarity, "value") else str(s.rarity),
            "secret": s.secret_token,
        }
        for s in secrets
    ]

    import json
    html = HTML_TEMPLATE.replace("{secrets_json}", json.dumps(secrets_data))

    out_path = Path(__file__).parent.parent / "qrs.html"
    out_path.write_text(html, encoding="utf-8")
    print(f"Exported {len(secrets)} QR codes to {out_path.absolute()}")


if __name__ == "__main__":
    asyncio.run(export_qrs())
