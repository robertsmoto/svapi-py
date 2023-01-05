from django.test import TestCase
from django.conf import settings
from svapi_py.api import SvApi
from datetime import datetime

CONF = settings.CONF

class SvApiTestCase(TestCase):
    def setUp(self):
        # instantiates the SvApi class, with the url and headers
        url = CONF.get('svapi', {}).get('host', '')
        headers = {
                'Aid': CONF.get('testsvapi', {}).get('aid', ''),
                'Auth': CONF.get('testsvapi', {}).get('auth', ''),
                'Prefix': CONF.get('testsvapi', {}).get('prefix', ''),
                'Content-Type': 'application/json'
                }
        self.svapi = SvApi(url, headers)

    def test_get_one(self):
        # wrong endpoint, should be 'document', not 'set'
        _, err =  self.svapi \
                .getOne('set', params={
                    'ID': '280e920d-6a15-4f61-a066-242df2f3b470' 
                    })
        self.assertTrue("Endpoint must be 'document'." in err)
        # non-existent or malformed ID
        _, err =  self.svapi \
                .getOne('document', params={
                    'ID': '280e920d-6a15-4f61-a066-242df2f3b471' 
                    })
        self.assertTrue('No data returned.' in err)
        # ID missing in request
        _, err =  self.svapi \
                .getOne('document', params={
                    'notID': '280e920d-6a15-4f61-a066-242df2f3b470' 
                    })
        self.assertTrue('code:400' in err)
        # correct request, ID (no paths)
        results, err =  self.svapi \
                .getOne('document', params={
                    'ID': '280e920d-6a15-4f61-a066-242df2f3b470' 
                    })
        # returns a python dict
        print("## reusults err", results, err)
        print("## results", results)
        self.assertTrue(isinstance(results, dict))
        # converts dt strings to dt objects
        self.assertTrue(isinstance(results['createdAt'], datetime))

    def test_get_many(self):
        # wrong endpoint, should be 'set', or 'search, not 'document'
        # returns 400 bad request
        _, err =  self.svapi \
                .getMany('document', params={
                    'setName': 'allSlugs',
                    'start': 0,
                    'end': -1
                    })
        self.assertTrue("Endpoint must be either 'search' or 'set'." in err)
        # non-existent endpoint
        # returns 404 not found
        _, err =  self.svapi \
                .getMany('endpoint_does_not_exists', params={
                    'setName': 'allSlugs',
                    'start': 0,
                    'end': -1
                    })
        self.assertTrue("Endpoint must be either 'search' or 'set'." in err)
        # non-existent setName
        # no data returned
        _, err =  self.svapi \
                .getMany('set', params={
                    'setName': 'nonexistent',
                    'start': 0,
                    'end': -1
                    })
        self.assertTrue("No data returned." in err)
        # no range specified, will return all
        results, err =  self.svapi \
                .getMany('set', params={
                    'setName': 'allSlugs'
                    })
        self.assertIsInstance(results, list)
        # range specified
        # 'set' endpoint returns a list of strings
        results, err =  self.svapi \
                .getMany('set', params={
                    'setName': 'allSlugs',
                    'start': 0,
                    'end': -1
                    })
        self.assertIsInstance(results, list)

        # 'search' endpoint returns a list of dicts
        err = ""
        results, err =  self.svapi \
                .getMany('search', params={
                    'docType': 'article'
                    })
        print("## err", err)
        print("## results", results, type(results))
        self.assertIsInstance(results, list)
