import re

from models.comment import Comment
from models.follow import Follow
from models.like import Like
from models.gift import Gift


class Formatter:
    @staticmethod
    def clean(text: str) -> str:
        text = re.sub(r"\s+", " ", text)
        return text.strip()

    @staticmethod
    def comment(comment: Comment) -> str:
        nickname = (
            comment.user.nickname
            or comment.user.username
            or "Alguien"
        )

        text = Formatter.clean(comment.text)

        return f"{nickname} dice: {text}"

    @staticmethod
    def follow(follow: Follow) -> str:
        nickname = (
            follow.user.nickname
            or follow.user.username
            or "Alguien"
        )

        return f"{nickname} comenzó a seguirte."

    @staticmethod
    def like(like: Like) -> str:
        nickname = (
            like.user.nickname
            or like.user.username
            or "Alguien"
        )

        return f"{nickname} envió {like.count} likes."

    @staticmethod
    def gift(gift: Gift) -> str:
        nickname = (
            gift.user.nickname
            or gift.user.username
            or "Alguien"
        )

        return f"{nickname} envió {gift.amount} {gift.gift_name}."