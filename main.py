"""
Main file
"""
from os import getenv

from dotenv import load_dotenv

from ade import ADEClient, Category, Classroom, Unite, Instructor, Event
from ade.elements import Activity
from database import Database

load_dotenv()

client = ADEClient(url=getenv("ADE_URL"), login=getenv("ADE_LOGIN"), password=getenv("ADE_PASSWORD"))
print("> Connection to ADE...")
client.connect()
client.set_project(getenv("ADE_PROJECT_ID"))
print("> Connected", end="\n\n")

print("> Fetching resources from ADE... (1/3)")
raw_resources = client.get_resources()

print("> Fetching events from ADE... (2/3)")
raw_events = client.get_events()

print("> Fetching activities from ADE... (3/3)", end="\n\n")
raw_activities = client.get_activities()

print("> Analyzing resources...")
classrooms = []
instructors = []
unites = []
for resource in raw_resources.iter(tag="resource"):
    category = resource.get("category")
    if category == Category.CLASSROOM:
        classrooms.append(Classroom.from_element(resource))
    elif category == Category.UNITE:
        unites.append(Unite.from_element(resource))
    elif category == Category.INSTRUCTOR and resource.get("isGroup") == "false":
        instructors.append(Instructor.from_element(resource))

print("> Analyzing events...")
events = []
for event in raw_events.iter(tag="event"):
    events.append(Event.from_element(event))

print("> Analyzing activities...", end="\n\n")
activities = []
for activity in raw_activities:
    activities.append(Activity.from_element(activity))

database = Database()
with database.transaction():
    print("> Clean existing tables...")
    database.clean()

    # populate resources tables
    print("> Populate resources tables")
    database.populate_classrooms(classrooms)
    database.populate_instructors(instructors)
    database.populate_unites(unites)

    # populate events
    print("> Populate events tables")
    database.populate_events(events)

    # update events with activities
    database.populate_activities(activities)

database.close()
