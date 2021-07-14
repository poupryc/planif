"""
Interacts with the ADE Web API.

Generally, this API is accessible via the usual url of ADE followed by ``/jsp/webapi``. The options (such as
``detail``) are passed as query string in this URL.

The features of the ADE Web API implemented here are the following:
    getEvents
    getActivities
    getResources
"""

# noinspection PyPep8Naming
import xml.etree.ElementTree as ET
from typing import Optional, Union

import requests


class ADEClient:
    """
    Interact with the ADE Web API.
    """
    url: str
    login: str
    password: str

    sessionId: Optional[str] = None
    projectId: Optional[str] = None

    def __init__(self, url, login, password=""):
        """
        Create a new ADE Web API client

        :param url: url of the ADE Web API
        :param login: login of the used ADE account
        :param password: password of the used ADE account
        :raise ValueError: if values supplied are not correct
        """
        if url is None:
            raise ValueError("A correct URL must be provided")

        self.url = url
        self.login = login
        self.password = password

    def connect(self) -> str:
        """
        Connect to the ADE server

        :return: the id of the new session
        """
        function = "connect"

        element = self._send(function, url=self.url, login=self.login, password=self.password)
        self.sessionId = element.get("id")

        return self.sessionId

    def get_projects(self, detail=1, **params):
        """
        Get the list of the ADE projects

        :param detail: degree of details of the response (high number will result in a longer waiting time)
        :param params: others options to be included in the request query string
        :return:
        """
        function = "getProjects"

        return self._send(function, detail=detail, **params)

    def set_project(self, project_id: Union[str, int], **params):
        """
        Set the project ID to use

        :param project_id: the ADE project ID to use with the ADE API
        :param params: others options to be included in the request query string
        """
        function = "setProject"

        self._send(function, projectId=project_id, **params)
        self.projectId = project_id

        # TODO: return something?

    def disconnect(self) -> str:
        """
        Disconnect from the ADE server

        :return: the id of the disconnected session
        """
        function = "disconnect"

        element = self._send(function)
        self.sessionId = None

        return element.get("sessionId")

    def get_events(self, detail=8, **params) -> ET.Element:
        """
        Get all the events from the current ADE project

        :param detail: degree of details of the response (high number will result in a longer waiting time)
        :param params: others options to be included in the request query string
        :return: the XML response element representing the events
        """
        function = "getEvents"
        element = self._send(function, detail=detail, **params)

        return element

    def get_activities(self, detail=11, **params) -> ET.Element:
        """
        Get all the available activities from the current ADE project

        :param detail: degree of details of the response (high number will result in a longer waiting time)
        :param params: others options to be included in the request query string
        :return:
        """
        function = "getActivities"
        element = self._send(function, detail=detail, **params)

        return element

    def get_resources(self, detail=11, **params) -> ET.Element:
        """
        Get all the available resources from the current ADE project

        :param detail: degree of details of the response (high number will result in a longer waiting time)
        :param params: others options to be included in the request query string
        :return: the XML response element representing the resources
        """
        function = "getResources"
        element = self._send(function, detail=detail, **params)

        return element

    def _send(self, function: str, **params) -> ET.Element:
        """
        Send a request to the ADE server and parse the XML response

        :param function: function name to be executed by the API
        :param params: dictionary of params to send in the query string
        :return: the XML element produced by the API
        :raise ConnectionError: if the connection was not successful
        """
        params["function"] = function

        if self.sessionId is not None:
            params["sessionId"] = self.sessionId

        response = requests.get(self.url, params=params)
        if response.status_code != 200:
            raise ConnectionError(
                "Status code of the response is {}. Maybe check the URL?".format(response.status_code))

        # there is a possibility that the answer is empty. This may be due to the use of an unknown function.
        if len(response.content) == 0:
            raise ConnectionError("The response seems to be empty. Maybe the function used is unknown for ADE?")

        if params["function"] == "getActivities":
            with open("activities.xml", "w") as file:
                file.write(response.text)

        element = ET.fromstring(response.text)

        # ADE responds with a 200 even in case of failure, with the only. The error message will be in the response XML.
        if element.tag == "error":
            msg = element.get("name")
            raise ConnectionError("Error raised during connection: {}".format(msg))

        return element
