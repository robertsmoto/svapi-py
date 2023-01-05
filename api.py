from django.conf import settings
from urllib.parse import urljoin
import logging
import requests
import json
from typing import Tuple, List
from datetime import datetime
from requests.exceptions import ConnectionError
from django.http import HttpRequest
from dateutil import parser
import string
from collections import Counter
from nltk.corpus import stopwords
from cmsapp.constants import Version, CURRENT_VERSION

logger = logging.getLogger('custom.logger')
CONF = settings.CONF


class SvApi():
    """Main class for interacting with the SVapi."""

    def __init__(self, request: HttpRequest):
        url = CONF.get('svapi', {}).get('host', '')
        self.url = url
        self.headers = {
            'Aid': request.session.get(request.user.id, '').get('aid', ''),
            'Auth': request.session.get(request.user.id, '').get('auth', ''),
            'Prefix': request.session.get(request.user.id, '').get('prefix'),
            'Content-Type': 'application/json'
        }

    def __dt_fromTimeStamp(self, data: float) -> datetime:
        try:
            dt = datetime.fromtimestamp(data)
        except Exception as e:
            print("## exception", e)
            dt = datetime.now()
        return dt

    def __dt_toTimeStamp(self, data: datetime) -> float:
        try:
            return datetime.timestamp(data)
        except Exception:
            return datetime.timestamp(datetime.now())

    def __dt_decoder(self, data: dict) -> dict:
        """Checks for certain dt strings and converts them to dt objects."""
        createdAt = int(data.get('createdAt', '0'))
        data['createdAt'] = self.__dt_fromTimeStamp(createdAt)
        data['updatedAt'] = datetime.now()
        return data

    def __dt_encoder(self, data: dict) -> dict:
        """Checks for certain dt objects and converts them to dt strings."""
        createdAt = data.get('createdAt', datetime.now())
        if isinstance(createdAt, str):
            createdAt = parser.parse(createdAt)
        data['createdAt'] = self.__dt_toTimeStamp(createdAt)
        updatedAt = data.get('updatedAt', datetime.now())
        if isinstance(updatedAt, str):
            updatedAt = parser.parse(updatedAt)
        data['updatedAt'] = self.__dt_toTimeStamp(updatedAt)
        return data

    def __word_frequency(self, data: str) -> str:
        # Split the text into words
        words = data.split()
        # Remove punctuation from each word
        table = data.maketrans('', '', string.punctuation)
        stripped_words = [w.translate(table) for w in words]
        # Remove remaining tokens that are not alphabetic
        words = [word for word in stripped_words if word.isalpha()]
        # Convert all words to lowercase
        words = [word.lower() for word in words]
        # Filter out stop words
        stop_words = set(stopwords.words('english'))
        words = [w for w in words if w not in stop_words]
        # Count the frequency of each word
        word_counts = Counter(words)
        # Sort the 10 most common words in descendng order
        most_common = word_counts.most_common(10)
        # Return the list as a string
        return ' '.join([x[0] for x in most_common])

    def getOne(self, endpoint: str, params: dict) -> Tuple[dict, str]:
        """Get one object from SodaVault. Returns tuple (dict,str). The
        str is an error message if any.Requires ?ID=<UUID> example:
        svapi = SvApi(host_url, headers)
        results, err = svapi.getOne('document', params={
                'ID': '<UUID>'
                })"""
        # check endpoint
        if endpoint != 'document':
            return {}, "Endpoint must be 'document'."

        url = urljoin(self.url, endpoint)
        try:
            response = requests.get(url, params=params, headers=self.headers)
        except ConnectionError as e:
            return {}, f"Error: {e} Please check the documentation."
        if response.status_code != 200:
            c = response.status_code
            r = response.reason
            return {}, f"code:{c} reason:{r}"
        if response.text == 'null':
            return {}, "No data returned."
        results = self.__dt_decoder(response.json())
        return results, ""

    def getMany(self, endpoint: str, params: dict) -> Tuple[List[dict], str]:
        """Get many objects from SodaVault. Returns Tuple[List[dict], str]. The
        str is an error message if any. Requires ?slug=<string> example:
        svapi = SvApi(host_url, headers)
        results, err = svapi.getMany('set', params={
                'slug': '<string>'
                })"""
        # check endpoint
        if endpoint != 'search' and endpoint != 'set':
            return [{}], "Endpoint must be either 'search' or 'set'."
        url = urljoin(self.url, endpoint)
        try:
            response = requests.get(url, params=params, headers=self.headers)
        except ConnectionError as e:
            return [{}], f"Error: {e} Please check the documentation."
        if response.status_code != 200:
            c = response.status_code
            r = response.reason
            return [{}], f"code:{c} reason:{r}"
        if response.text == 'null':
            return [{}], "No data returned."
        if endpoint == 'set':
            return [x for x in response.json()], ''
        return [self.__dt_decoder(x) for x in response.json()], ''

    def makeChoices(self, resultList: list, choiceID: str, choiceHuman: str
                    ) -> List[Tuple[str, str]]:
        """Creates choices list of tuples from given query."""
        return [(x.get(choiceID, ''), x.get(choiceHuman, ''))
                for x in resultList]

    def add(self, endpoint: str, *args, **kwargs) -> requests.Response:
        # serialize the data and account for special values such as dt
        data = kwargs.get('data', {})
        # convert QueryDict to regular python dict
        data = self.__dt_encoder(data.dict())
        # remove the csrfmiddleware token
        del data['csrfmiddlewaretoken']
        # cast schemaVersion str to int
        schemaVersion = data.get('schemaVersion', '')
        if not schemaVersion:
            schemaVersion = Version.V2023_01.value
        if CURRENT_VERSION.value > int(schemaVersion):
            schemaVersion = CURRENT_VERSION.value
        data['schemaVersion'] = int(schemaVersion)
        # make the word frequency indx if not present
        indx = data.get('indx', '')
        if indx == '':
            name = data.get('name', '')
            description = data.get('description', '')
            data['indx'] = self.__word_frequency(' '.join([name, description]))
        print("## data.createdAt", data['createdAt'], type(data['createdAt']))
        params = kwargs.get('params', {})
        url = urljoin(self.url, endpoint)
        print("## data json", json.dumps(data))
        response = requests.post(
            url,
            params=params,
            data=json.dumps(data),
            headers=self.headers)
        print("## response.text", response.text)
        return response

    def modify(self, endpoint: str, data: dict) -> requests.Response:
        # serialize the data and account for special values such as dt
        data = self.__dt_encoder(data)
        url = urljoin(self.url, endpoint)
        jsonData = json.dumps(data)
        response = requests.post(
            url,
            data=jsonData,
            headers=self.headers)
        return response

    def delete(self, endpoint: str, *args, **kwargs) -> str:
        params = kwargs.get('params', '')
        url = urljoin(self.url, endpoint)
        response = requests.delete(url, params=params, headers=self.headers)
        return response
