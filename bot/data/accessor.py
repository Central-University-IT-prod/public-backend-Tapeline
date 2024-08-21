"""
Helper functions for accessing data and working with ORM models
"""

import datetime
import uuid

from bot.api.nominatim import NominatimAPI
from bot.data.models import User, Trip, TripPoint, Note, Debt


class UserAccessor:
    """Helper for User model and related stuff"""
    @classmethod
    def user_registered(cls, user_id: int) -> bool:
        """Check if user is registered in this bot"""
        return User.select().where(User.tg_id == user_id).exists()

    @classmethod
    def convert_tg_user(cls, user) -> User:
        """Converts aiogram user to ORM user"""
        return cls.convert_tg_id_user(user.id)

    @classmethod
    def convert_tg_id_user(cls, user_id: int) -> User:
        """Converts aiogram user to ORM user"""
        return User.get(User.tg_id == user_id)

    @classmethod
    def register_user(cls, user_id: int, user_data: dict, tg_user) -> None:
        """Perform registration"""
        user = User(
            year_of_birth=datetime.date.today().year - user_data["age"],
            bio=user_data["bio"],
            city_osm_id=user_data["city"].id,
            city_osm_type=user_data["city"].type,
            city_name=user_data["city"].name,
            tg_id=user_id,
            interests=user_data["interests"],
            gender=user_data["gender"],
            username=tg_user.username
        )
        user.save()

    @classmethod
    def get_age(cls, user: User) -> int:
        """Helper for getting user age"""
        return datetime.date.today().year - user.year_of_birth


class TripAccessor:
    """Helper for Trip model and related stuff"""
    @classmethod
    def get_owned_by_user(cls, user: User) -> list[Trip]:
        return list(Trip.filter(Trip.owner == user))

    @classmethod
    def get_where_participates(cls, user: User) -> list[Trip]:
        return list(filter(lambda x: user in x.participants, list(Trip.select())))

    @classmethod
    def get_all_by_user(cls, user: User) -> list[Trip]:
        return cls.get_owned_by_user(user) + cls.get_where_participates(user)

    @classmethod
    def get_points_in_trip(cls, trip_id: int) -> list[TripPoint]:
        trip = Trip.get_by_id(trip_id)
        points = {p.get_id(): p for p in TripPoint.filter(TripPoint.related_trip == trip)}
        return list(map(lambda x: points[x], list(map(int, trip.points.split()))))

    @classmethod
    def get_prev_point_lat_lon(cls, trip_id: int, point_id: int):
        trip = Trip.get_by_id(trip_id)
        points = list(map(int, trip.points.split()))
        if points.index(point_id) == 0:
            return trip.start_point_lat, trip.start_point_lon
        prev_point = TripPoint.get_by_id(points[points.index(point_id) - 1])
        return prev_point.lat, prev_point.lon

    @classmethod
    def is_owner(cls, trip_id, user):
        return Trip.get_by_id(trip_id).owner == user

    @classmethod
    def create_point(cls, user, user_point_data, trip_id):
        trip = Trip.get_by_id(trip_id)
        point = TripPoint(
            name=user_point_data["name"],
            lat=user_point_data["lat"],
            lon=user_point_data["lon"],
            osm_id=user_point_data["osm_id"],
            osm_type=user_point_data["osm_type"],
            city_name=user_point_data["city_name"],
            city_osm_id=user_point_data["city_id"],
            related_trip=trip,
            start_date=user_point_data["start"],
            end_date=user_point_data["end"]
        )
        point.save()
        points = trip.points.split()
        points.append(str(point.get_id()))
        trip.points = " ".join(points)
        trip.save()

    @classmethod
    def remove_point(cls, point_id, trip_id):
        point = TripPoint.get_by_id(point_id)
        point.delete_instance()
        trip = Trip.get_by_id(trip_id)
        points = trip.points.split()
        points.remove(str(point_id))
        trip.points = " ".join(points)
        trip.save()

    @classmethod
    def regen_invitation(cls, trip_id):
        trip = Trip.get_by_id(trip_id)
        key = str(uuid.uuid4())
        trip.invitation = key
        trip.save()

    @classmethod
    def create_trip(cls, orm_user, user_trip_data):
        lat, lon = NominatimAPI.get_lat_lon_by_id(orm_user.city_osm_id)
        trip = Trip(
            owner=orm_user,
            name=user_trip_data["name"],
            description=user_trip_data["desc"],
            start_date=user_trip_data["start"],
            end_date=user_trip_data["end"],
            start_point_lat=lat,
            start_point_lon=lon,
            invitation=str(uuid.uuid4())
        )
        trip.save()

    @classmethod
    def get_trip_to_join(cls, invitation, user_tg_id) -> Trip:
        possible_trips = list(Trip.filter(Trip.invitation == invitation))
        if len(possible_trips) == 0:
            raise ValueError("Invalid invitation key")
        if len(possible_trips) > 1:
            raise ValueError("Bad invitation key.\n"
                             "Please request trip admin to regenerate "
                             "invitation key")
        trip = possible_trips[0]
        if UserAccessor.convert_tg_id_user(user_tg_id) in trip.participants or \
            trip.owner == UserAccessor.convert_tg_id_user(user_tg_id):
            raise ValueError("Already participating")
        return trip


class NoteAccessor:
    @classmethod
    def get_notes_for_user(cls, trip_id, user_id):
        user = User.get_by_id(user_id)
        trip = Trip.get_by_id(trip_id)
        objects = list(Note.select())
        # for some reason does not work on postgres
        # return list(Note.filter(Note.related_trip == trip & Note.is_public | Note.owner == user))
        return list(filter(lambda x: x.related_trip == trip and x.is_public or x.owner == user, objects))

    @classmethod
    def create_note(cls, user, user_note_data, trip_id):
        trip = Trip.get_by_id(trip_id)
        note = Note(
            name=user_note_data["name"],
            tg_message_ids=" ".join(map(str, user_note_data["messages"])),
            related_trip=trip,
            owner=UserAccessor.convert_tg_user(user),
            is_public=user_note_data["is_public"],
            tg_chat_id=user_note_data["chat"]
        )
        note.save()


class DebtAccessor:
    @classmethod
    def create_debt(cls, trip, recipient, amount, users):
        per_user_amount = amount / len(users)
        for user in users:
            debt = Debt(
                related_trip=trip,
                recipient=recipient,
                debtor=user,
                amount=per_user_amount
            )
            debt.save()

    @classmethod
    def total_debts_amount(cls, trip, user):
        debts = list(filter(lambda x: x.debtor == user and x.related_trip == trip, list(Debt.select())))
        return sum(map(lambda x: x.amount, debts)), debts

    @classmethod
    def total_settlement_amount(cls, trip, user):
        debts = list(filter(lambda x: x.recipient == user and x.related_trip == trip, list(Debt.select())))
        return sum(map(lambda x: x.amount, debts)), debts
