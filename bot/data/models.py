import datetime

from peewee import Model, PostgresqlDatabase, BooleanField, IntegerField, CharField, TextField, ForeignKeyField, \
    ManyToManyField, FloatField, DateField, SqliteDatabase

#db = SqliteDatabase('sqlite.db', pragmas={'journal_mode': 'wal'})
db = PostgresqlDatabase(database="database", host="postgres", port=5432,
                        user="bot_user", password="bot_db_password")


def init():
    db.connect()
    db.create_tables([User, Trip, Trip.participants.get_through_model(), TripPoint, Note, Debt])


class BaseModel(Model):
    class Meta:
        database = db


class User(BaseModel):
    gender = BooleanField()
    city_osm_id = IntegerField()
    city_osm_type = CharField(default="R")
    city_name = CharField(max_length=255)
    year_of_birth = IntegerField()
    bio = TextField(null=True)
    tg_id = IntegerField()
    interests = TextField()
    display_in_explore = BooleanField(default=True)
    tg_username = CharField(max_length=255, null=True)


class Trip(BaseModel):
    start_point_lat = FloatField()
    start_point_lon = FloatField()
    name = CharField(max_length=255, unique=True)
    description = TextField(null=True)
    owner = ForeignKeyField(User)
    participants = ManyToManyField(User)
    start_date = DateField()
    end_date = DateField()
    points = TextField(default="")
    invitation = CharField(max_length=255)


class TripPoint(BaseModel):
    lat = FloatField()
    lon = FloatField()
    city_name = CharField(max_length=255)
    osm_id = IntegerField()
    osm_type = CharField(max_length=1)
    city_osm_id = IntegerField()
    name = CharField(max_length=255)
    related_trip = ForeignKeyField(Trip)
    start_date = DateField()
    end_date = DateField()


class Note(BaseModel):
    tg_message_ids = TextField()
    tg_chat_id = IntegerField()
    related_trip = ForeignKeyField(Trip)
    owner = ForeignKeyField(User)
    is_public = BooleanField(default=False)
    name = CharField(max_length=255)


class Debt(BaseModel):
    debtor = ForeignKeyField(User)
    recipient = ForeignKeyField(User)
    amount = FloatField()
    date = DateField(default=datetime.datetime.now)
    related_trip = ForeignKeyField(Trip)


INTEREST_TAGS = {
    "TV",
    "Video games",
    "Singing",
    "Cars",
    "Reading",
    "Shopping",
    "Movies",
    "Fashion",
    "Music",
    "Drawing",
    "Writing",
    "Photography",
    "Woodworking",
    "Sports",
    "Politics",
    "Languages",
    "Programming",
    "DIY",
    "Cycling",
    "Walking",
    "Dancing",
    "Fishing"
}
