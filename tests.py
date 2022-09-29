from django.test import TestCase
from .graphql import QueryData, Query

class AnimalTestCase(TestCase):

    def test_qstr_constructor(self):
        """Test qstring constructor."""
        q = Query('test:key', [
            QueryData(alias='products', typeArg='product', children=True),
            QueryData(alias='brands', typeArg='brand'),
            QueryData(alias='categories', typeArg='categoryProduct')
            ])
        q._constructor_hasher()
        print("## qstr -->", q.qstr)
