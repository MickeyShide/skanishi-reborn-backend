from pydantic import BaseModel


class ReferralStatsResponse(BaseModel):
    referral_link: str
    total_friends: int
    friends_list: list[str]
