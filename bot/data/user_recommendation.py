"""Provides utilities for recommending users"""
# pylint: disable=C0115
# pylint: disable=C0116

from bot.data.accessor import UserAccessor


class UserRecommendation:
    @classmethod
    def _get_score_for_user_pair(cls, matching_to_user, user):
        """Utility function"""
        age_score = 1 - abs(UserAccessor.get_age(matching_to_user) - UserAccessor.get_age(user)) / 5

        matching_interests = 0
        interests_a = matching_to_user.interests.split("\n")
        interests_b = user.interests.split("\n")
        for i in interests_a:
            if i in interests_b:
                matching_interests += 1
        interest_score = matching_interests / len(interests_a)

        return age_score * 0.3 + interest_score * 0.7

    @classmethod
    def list_recommended_users(cls, matching_to_user, users, limit=15):
        users = list(filter(lambda x:
                            abs(UserAccessor.get_age(x) - UserAccessor.get_age(matching_to_user)) <= 5,
                            users))
        users = sorted(users, key=lambda x: cls._get_score_for_user_pair(matching_to_user, x),
                       reverse=True)
        users = list(filter(lambda x: x.get_id() != matching_to_user.get_id(), users))
        return users[:min(limit, len(users))]
