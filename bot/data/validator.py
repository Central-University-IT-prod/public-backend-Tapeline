from bot.data.models import INTEREST_TAGS


def validate_interests(text):
    interests = text.split("\n")
    for i in interests:
        if i not in INTEREST_TAGS:
            return False
    return True
