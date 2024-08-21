from bot.data.user_recommendation import UserRecommendation


class FakeUser:
    def __init__(self, name, interests, year_of_birth):
        self.name = name
        self.interests = interests
        self.year_of_birth = year_of_birth

    def get_id(self):
        return self.name

    def __repr__(self):
        return self.name


def test_user_recommendations():
    user1 = FakeUser("1", "TV\nSinging\nCars", 2001)
    user2 = FakeUser("2", "TV\nSinging\nCars", 1998)
    user3 = FakeUser("3", "TV\nSinging\nPolitics", 2004)
    user4 = FakeUser("4", "TV\nSinging\nCars", 1950)
    user5 = FakeUser("5", "TV\nSinging\nPolitics\nVideo games", 2001)
    rec = UserRecommendation.list_recommended_users(user1, [user1, user2, user3, user4, user5])
    assert len(rec) == 3
    assert rec[0].name == "2"
    assert rec[1].name == "5"
    assert rec[2].name == "3"
