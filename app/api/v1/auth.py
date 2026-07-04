import json
from json import JSONDecodeError
from typing import Annotated
from urllib.parse import parse_qsl

from fastapi import APIRouter, Depends, Request, Response, status
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError

from app.api.v1.dependencies import CurrentUser, enforce_csrf_protection
from app.schemas.auth import TelegramAuthRequest, TokenResponse
from app.schemas.user import UserMe
from app.services.business.auth import AuthBusinessService

router = APIRouter(prefix="/auth", tags=["Auth"])


AUTH_INIT_OPENAPI_EXTRA = {
    "requestBody": {
        "required": True,
        "content": {
            "application/x-www-form-urlencoded": {
                "schema": {
                    "type": "object",
                    "required": ["tg_web_app_data"],
                    "properties": {
                        "tg_web_app_data": {
                            "type": "string",
                            "minLength": 1,
                            "maxLength": 4096,
                        },
                    },
                },
            },
            "application/json": {
                "schema": TelegramAuthRequest.model_json_schema(),
            },
        },
    },
}


async def parse_telegram_auth_request(request: Request) -> TelegramAuthRequest:
    content_type = request.headers.get("content-type", "").lower()
    raw_body = await request.body()
    data: object

    if "application/x-www-form-urlencoded" in content_type:
        data = dict(parse_qsl(raw_body.decode(), keep_blank_values=True))
    elif raw_body:
        try:
            data = json.loads(raw_body)
        except JSONDecodeError:
            data = dict(parse_qsl(raw_body.decode(), keep_blank_values=True))
    else:
        data = {}

    try:
        return TelegramAuthRequest.model_validate(data)
    except ValidationError as exc:
        raise RequestValidationError(exc.errors()) from exc


@router.post(
    "/init", response_model=TokenResponse, openapi_extra=AUTH_INIT_OPENAPI_EXTRA
)
async def auth_init(
    dto: Annotated[TelegramAuthRequest, Depends(parse_telegram_auth_request)],
    request: Request,
    response: Response,
):
    return await AuthBusinessService().authenticate(
        dto=dto, request=request, response=response
    )


@router.post(
    "/refresh",
    response_model=TokenResponse,
    dependencies=[Depends(enforce_csrf_protection)],
)
async def auth_refresh(request: Request, response: Response):
    return await AuthBusinessService().refresh(request=request, response=response)


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(enforce_csrf_protection)],
)
async def auth_logout(request: Request, response: Response) -> None:
    await AuthBusinessService().logout(request=request, response=response)


@router.get("/me", response_model=UserMe)
async def auth_me(current_user: CurrentUser):
    return UserMe.model_validate(current_user)
