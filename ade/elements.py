"""
Objects representing the information retrieved by the ADE API.

The purpose of these classes is to convert XML data into Python objects.
"""
import enum
import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, List
from xml.etree.ElementTree import Element

import arrow


@enum.unique
class Category(str, Enum):
    """Possible categories for an ADE resource"""
    CLASSROOM = "classroom"
    INSTRUCTOR = "instructor"
    TRAINEE = "trainee"
    UNITE = "category6"


@dataclass
class Classroom:
    """A classroom is a location where an event take place"""
    id: int
    name: str
    category: Optional[str] = field(default=None)

    @classmethod
    def from_element(cls, element: Element) -> "Classroom":
        """
        Construct a Classroom from the data of an XML element.
        The XML element must look like this:

        ``<resource id="..." category="classroom" name="5407V" fatherName="08-Labos" info="..." ... />``

        :param element: the XML element used to build the object
        :return: the Classroom constructed
        """

        # removes the unnecessary prefix (some folder id) of the room category
        prefix_id = re.compile(r"^\d+-")

        id = int(element.get("id"))
        name = element.get("name")

        category = None
        if "fatherName" in element.attrib:
            category = prefix_id.sub("", element.get("fatherName"))

        return cls(id=id, name=name, category=category)


@dataclass
class Instructor:
    """An instructor is a person participating in an event, typically a teacher"""
    id: int
    name: str
    department: Optional[str] = field(default=None)

    @classmethod
    def from_element(cls, element: Element) -> "Instructor":
        """
        Construct an Instructor from the data of an XML element.
        The XML element must look like this:

        ``<resource id="360" name="MAIRESSE Je." path="ESIEE PARIS 2020-2021._Administratifs." category="instructor"
        fatherName="_Administratifs"code="Jean" ... />``

        :param element: the XML element used to build the object
        :return: the Instructor constructed
        """
        id = int(element.get("id"))

        human_name = re.compile(r"^(.*) \w+.$")

        name = element.get("name")

        # the instructor could be a company or an human
        if "sté" in name.lower():
            name = name.replace("Sté ", "Société ")
        elif human_name.match(name):
            name = "{} {}".format(element.get("code"), human_name.match(name).group(1))

        name.strip()

        department = None
        if "path" in element.attrib:
            department = element.get("path")
            department = department.split(".")[1]

            # some department are prefixed with "_" like "_Administratifs"
            department = department.removeprefix("_")

        return cls(id=id, name=name, department=department)


@dataclass
class Trainee:
    """A Trainee is a group following common teachings"""
    pass


@dataclass
class Unite:
    """An Unite can be a subject or a set of subjects chosen for their coherence in this set"""
    id: Optional[int]
    name: Optional[str]
    code: str
    branch: Optional[str]
    label: Optional[str] = field(default=None)

    @classmethod
    def from_element(cls, element: Element) -> "Unite":
        """
        Construct an Unite from the data of an XML element.
        The XML element must look like this:

        ``<resource id="..." category="category6" name="IGI-1104" fatherName="E1" code="E1_IGI_1104" ... />``

        :param element: the XML element used to build the object
        :return: the Unite constructed
        """
        id = int(element.get("id"))
        name = element.get("name")

        code = None
        if "code" in element.attrib:
            code = element.get("code")

        branch = None
        if "fatherName" in element.attrib:
            branch = element.get("fatherName")

        return cls(id=id, name=name, code=code, branch=branch)


@dataclass
class Event:
    """An event is an occurrence of an activity"""
    id: int
    activity_id: int
    name: str
    start_at: datetime
    end_at: datetime
    unite: Optional[Unite] = field(default=None)
    instructors: list[Instructor] = field(default_factory=list)
    classrooms: list[Classroom] = field(default_factory=list)
    trainees: List[str] = field(default_factory=list)

    @classmethod
    def from_element(cls, element: Element) -> "Event":
        """
        Construct an Unite from the data of an XML element.
        The XML element must look like this:

        ``<event id="..." activityId="..." name="FLE-2:TD" endHour="19:00" startHour="17:00" date="02/03/2021" ... />``

        :param element: the XML element used to build the object
        :return: the Event constructed
        """
        id = int(element.get("id"))
        activity_id = int(element.get("activityId"))
        name = element.get("name")

        date = element.get("date")
        start_hour = element.get("startHour")
        end_hour = element.get("endHour")

        start_at = cls._to_datetime(date, start_hour)
        end_at = cls._to_datetime(date, end_hour)

        event = cls(id=id, activity_id=activity_id, name=name, start_at=start_at, end_at=end_at)

        # we iterate through resource elements in order to provide more information about the current event
        for resource in element.iter(tag="resource"):
            category = resource.get("category")

            if category == Category.CLASSROOM:
                event.classrooms.append(Classroom.from_element(resource))
            elif category == Category.INSTRUCTOR:
                event.instructors.append(Instructor.from_element(resource))
            elif category == Category.UNITE:
                event.unite = Unite.from_element(resource)
            elif category == Category.TRAINEE:
                event.trainees.append(resource.get("name"))

        return event

    @classmethod
    def _to_datetime(cls, date: str, hour: str) -> datetime:
        """
        Creates a datetime from a string representing a date and another representing a time.

        :param date: the date "day/month/year" to be used
        :param hour: the time "hour:minute" to be used
        :return: the datetime object created
        """
        expression = "{} {}".format(date, hour)

        # we assume that the date given by ADE are localized according to Paris timezone (UTC+02:00)
        moment = arrow.get(expression, "DD/MM/YYYY HH:mm").replace(tzinfo="Europe/Paris")

        return moment.to("utc").datetime


@dataclass
class Activity:
    """an activity is an abstract event, which has no date and contains various information"""
    id: int
    name: str
    description: str
    category: str
    info: str

    @classmethod
    def from_element(cls, element: Element) -> "Activity":
        """
        Construct an Activity from the data of an XML element.
        The XML element must look like this:

        ``<activity id="10135" name="3R-RS1:COURS" type="cours-1" code="Introduction aux réseaux : Modèles,
        Protocoles, Topologie" info="something" ... />``

        :param element: the XML element used to build the object
        :return: the Activity constructed
        """
        id = int(element.get("id"))
        name = element.get("name")
        description = element.get("code")
        category = element.get("type")
        info = element.get("info")

        return cls(id=id, name=name, description=description, category=category, info=info)
