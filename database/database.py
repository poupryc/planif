"""
Interact with the database
"""
from collections import Iterator
from contextlib import contextmanager
from typing import List, Tuple

import psycopg
from psycopg import Transaction

from ade import Classroom, Instructor, Unite, Event


class Database:
    """Interact with the data and the database"""
    connection: psycopg.Connection
    cursor: psycopg.Cursor

    """Abstraction around psycopg3 to interact with data"""

    def __init__(self, **conn):
        """
        Instantiate a new database connection

        :param conn: database connection information
        """
        self.connection = psycopg.connect(**conn)
        self.cursor = self.connection.cursor()

    @contextmanager
    def transaction(self) -> Iterator[Transaction]:
        """
        Start a context block with a new transaction.
        """
        with Transaction(self.connection, savepoint_name=None, force_rollback=False) as tx:
            yield tx

    def populate_classrooms(self, classrooms: List[Classroom]):
        """
        Populate classroom table into the database

        :param classrooms: list of classrooms to be added
        """
        sql = "COPY classrooms (id, name, category) FROM STDIN"

        def extract(item: Classroom) -> Tuple[int, str, str]:
            """
            Extract the tuple of data to insert in the database
            :param item: the unite to be used
            :return: the tuple of data
            """
            return item.id, item.name, item.category

        with self.cursor.copy(sql) as copy:
            for classroom in classrooms:
                copy.write_row(extract(classroom))

    def populate_instructors(self, instructors: List[Instructor]):
        """
         Populate instructor table into the database

         :param instructors: list of instructors to be added
         """
        sql = "COPY instructors (id, name, department) FROM STDIN"

        def extract(item: Instructor) -> Tuple[int, str, str]:
            """
            Extract the tuple of data to insert in the database
            :param item: the unite to be used
            :return: the tuple of data
            """
            return item.id, item.name, item.department

        with self.cursor.copy(sql) as copy:
            for instructor in instructors:
                copy.write_row(extract(instructor))

    def populate_unites(self, unites: List[Unite], aurion: List[Unite]):
        """
         Populate unite table into the database

         :param unites: list of unites from ADE to be added
         :param aurion: data from Aurion
         """
        unites_copy = "COPY unites (id, name, code, branch) FROM STDIN"

        with self.cursor.copy(unites_copy) as copy:
            for unite in unites:
                data = (unite.id, unite.name, unite.code, unite.branch)
                copy.write_row(data)

        self.cursor.execute("""
            CREATE TEMPORARY TABLE IF NOT EXISTS aurion_unites_temp
            (
                code    TEXT,
                label   TEXT
            );
        """)

        aurion_unites_copy = "COPY aurion_unites_temp (code, label) FROM STDIN"

        with self.cursor.copy(aurion_unites_copy) as copy:
            for unite in aurion:
                data = (unite.code, unite.label)
                copy.write_row(data)

        self.cursor.execute("""
            UPDATE unites
                SET label = unite.label
                FROM aurion_unites_temp AS unite
                WHERE unites.code = unite.code
        """)

    def populate_events(self, events: List[Event]):
        """
         Populate event table into the database

         :param events: list of unites to be added
         """
        events_copy = "COPY events (id, activity_id, name, start_at, end_at, unite_id) FROM STDIN"

        # we populate the "events" table with the specific data
        with self.cursor.copy(events_copy) as copy:
            for event in events:
                data = (event.id, event.activity_id, event.name, event.start_at, event.end_at,
                        getattr(event.unite, "id", None))
                copy.write_row(data)

        # then we introduce the relation to the others data
        # we populate the table "events_classrooms", as this is a many-to-many relation
        events_classrooms_copy = \
            "COPY events_classrooms (event_id, classroom_id) FROM STDIN"

        with self.cursor.copy(events_classrooms_copy) as copy:
            for unite in events:
                seen = set()
                for classroom in unite.classrooms:
                    # because ADE allows duplicate classrooms, we need to be sure that
                    # the tuple (unite.id, classroom.id) is unique for Postgresql
                    if (unite.id, classroom.id) in seen:
                        continue

                    seen.add((unite.id, classroom.id))
                    copy.write_row((unite.id, classroom.id))

        # we do the same for "events_instructors" as this is a m:m relation too
        events_instructors_copy = "COPY events_instructors (event_id, instructor_id) FROM STDIN"
        with self.cursor.copy(events_instructors_copy) as copy:
            for unite in events:
                for instructor in unite.instructors:
                    copy.write_row((unite.id, instructor.id))

    def populate_activities(self, activities):
        """
        Populate activity table into the database

        :param activities: list of activities to be added
        """
        self.cursor.execute("""
            CREATE TEMPORARY TABLE IF NOT EXISTS activities_temp
            (
                id INTEGER PRIMARY KEY,
                description TEXT,
                category TEXT,
                info TEXT
            );
        """)

        activities_sql = "COPY activities_temp (id, description, category, info) FROM STDIN"

        with self.cursor.copy(activities_sql) as copy:
            for activity in activities:
                data = (activity.id, activity.description, activity.category, activity.info)
                copy.write_row(data)

        # we must remember that ADE gives us the following guarantee
        # - an event necessarily has an associated activity
        # - an activity may not have an event
        # so we do the data fusion in order to keep the activities with an associated event

        # it is better to do this merge on the Postgresql side than on the Python side because the database is much
        # more efficient on several orders of magnitude for this kind of operation

        self.cursor.execute("""
            UPDATE events
                SET description = activity.description,
                    category = activity.category,
                    info = activity.info
                FROM activities_temp AS activity
                WHERE events.activity_id = activity.id
        """)

    def clean(self):
        """
        Clean existing tables in the database.
        """
        truncate_sql = "TRUNCATE classrooms, events, events_classrooms, events_instructors, instructors, unites"

        self.cursor.execute(truncate_sql)

    def close(self):
        """Close the database connection"""
        self.cursor.close()
        self.connection.close()
