"""
Interacts with the Web Aurion API.

This API is not publicly available. It depends on requests specified by the administrator of your instance and an
account with special permissions.
"""
import requests
# noinspection PyPep8Naming
import xml.etree.ElementTree as ET
from ade.elements import Unite


class AurionClient:
    """
    Interact with the Web Aurion API.
    """
    url: str
    login: str
    password: str
    database: str

    def __init__(self, url, login, password, database):
        """
        Create a new Web Aurion API client

        :param url: URL of the Aurion server
        :param login: login of the account to be used
        :param password: password of the account to be used
        """
        if url is None:
            raise ValueError("A correct URL must be provided")

        self.url = url
        self.login = login
        self.password = password
        self.database = database

    def retrieve_unites(self) -> list[Unite]:
        """
        Extract the name of the units with the associated code

        :return: a list of unites with a code and a full description
        """
        data = self._send(18152939)

        unites = []
        for row in data.iter(tag="row"):
            code = row.find("Code.Unité").text[3:]  # remove "E1_"
            label = row.find("Libellé.Unité").text

            if label:
                label = label.strip()

            unites.append(Unite(code=code, label=label, branch=None, id=None, name=None))

        return unites

    def _send(self, request_id) -> ET.Element:
        """
        Execute a specific request

        :param request_id: The request id to be executed by the API
        :return: the XML element produced by the API
        """
        payload = """
            <executeFavori>
                <favori><id>{request_id}</id></favori><database>{database}</database>
            </executeFavori>
        """

        data = dict(
            login=self.login,
            password=self.password,
            data=payload.format(request_id=request_id, database=self.database)
        )

        response = requests.post(self.url, data=data)
        element = ET.fromstring(response.text)

        return element
