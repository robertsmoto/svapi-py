from __future__ import annotations
from dataclasses import dataclass
from redis_py.redis import Redis
from typing import Literal, List, Generator
import hashlib
import json
import logging
import os
import requests

TIMEOUT = int(os.getenv('CACHE_TIMEOUT', '60'))  # seconds
SVREDIS = Redis(db=0).conn
logger = logging.getLogger('custom.logger')

@ dataclass
class QueryData:
    alias: str = ''
    ID: str = ''
    parentID: str = ''
    typeArg: str = ''
    docFilter: str = ''
    docFilterValue: str = ''
    sortBy: str = ''
    sort: Literal['ASC', 'DESC', ''] = ''
    children: bool = False
    pageInfo: bool = False
    first: int = 0
    before: str = ''
    after: str = ''

class Query:
    """Used with /query endpoint."""

    def __init__(self, cache_key: str, data_objs: List[QueryData]):
        self.cache_key = cache_key
        self.data_objs = data_objs

        alias_list = []
        for l in data_objs:
            alias_list.append(l.alias)
        self.alias_list = alias_list

        self.apihost = f"{os.getenv('SVAPI_HST', '')}"
        self.headers = {
                'Content-Type': os.getenv('SVAPI_CNT', ''),
                'Aid': os.getenv('SVAPI_AID', ''),
                'Auth': os.getenv('SVAPI_AUT', ''),
                'Prefix': os.getenv('SVAPI_PRE', '')
                }
        self.qstr = ''
        self.md5 = ''
        self.response = b''  # <-- bytes str
        # self.queryset = ''
        self.err = (0, '')
        self._query_checker_cacher()

    def __repr__(self):
        return self.response

    def _qstr_constructor(self, index: int, qstr: str) -> str:
        """Builds the query string needed for the query.
        Index = len(qstr_data)."""

        # reduce the index
        index -= 1
        obj = self.data_objs[index]

        def attrstr_builder(obj: QueryData) -> str:
            """Builds all possible attributes for each node."""
            def str_helper(key: str, data: str) -> str:
                if data:
                    return f'{key}:\\"{data}\\"'
                return ''
            def str_noquotes_helper(key: str, data: str) -> str:
                if data:
                    return f'{key}:{data}'
                return ''

            nid = str_helper('id', obj.ID)
            pid = str_helper('parentId', obj.parentID)
            typ = str_helper('type', obj.typeArg)
            dft = str_helper('docFilter', obj.docFilter)
            dfv = str_helper('docFilterValue', obj.docFilterValue)
            srb = str_helper('sortBy', obj.sortBy)
            srt = str_noquotes_helper('sort', obj.sort)
            first = ''
            if obj.first:
                first = str_noquotes_helper('first', str(obj.first))
            before = str_helper('before', obj.before)
            after = str_helper('after', obj.after)
            attr_list = [
                    nid, pid, typ, dft, dfv, srb, srt, first, before, after]
            return ','.join(x for x in attr_list if x)

        def pagestr_builder(obj: QueryData) -> str:
            page = (
                'pageInfo{startCursor,endCursor,hasNextPage,hasPreviousPage}'
                )
            if obj.pageInfo:
                return page
            return ''

        def childstr_builder(obj: QueryData) -> str:
            pstr = pagestr_builder(obj)
            cstr = (
                ',children{%(pstr)s'
                'edges{attributes,node{id,parentId,type,document,createdAt}}}'
                % {'pstr': pstr})
            if obj.children:
                return cstr
            return ''

        def connection_builder(obj: QueryData, qstr: str) -> str:

            if not obj.alias:
                self.err = (1, 'Alias is required in the query constructor')
            cstr = childstr_builder(obj)
            pstr = pagestr_builder(obj)
            atts = attrstr_builder(obj)

            s = (',%(alias)s:nodeConnection(%(atts)s)'
                    '{%(pstr)sedges{attributes,node{id,parentId,type,'
                    'document,createdAt%(cstr)s}}}'
                    % {
                        'alias': obj.alias,
                        'atts': atts,
                        'pstr': pstr,
                        'cstr': cstr
                        }
                    )
            return ' '.join([s, qstr])

        def node_builder(obj: QueryData, qstr: str) -> str:

            if not obj.alias:
                self.err = (1, 'Alias is required in the query constructor')
            cstr = childstr_builder(obj)
            pstr = pagestr_builder(obj)
            atts = attrstr_builder(obj)
            s = ('{"query": "{%(alias)s:nodes(%(atts)s)'
                    '{%(pstr)sedges{attributes,node{id,parentId,type,'
                    'document,createdAt%(cstr)s%(qstr)s}}}}"}'
                    % {
                        'alias': obj.alias,
                        'atts': atts,
                        'pstr': pstr,
                        'cstr': cstr,
                        'qstr': qstr
                        }
                    )
            return s.replace(' ', '')

        if index > 0:
            qstr = connection_builder(obj, qstr)

        if index == 0:  # we've reached the end
            return node_builder(obj, qstr)

        return self._qstr_constructor(index, qstr)


    def _md5_hasher(self) -> str:
        """Hashes the qstr which will be used as the redis cache key."""
        return hashlib.md5(self.qstr.encode('utf-8')).hexdigest()

    def _constructor_hasher(self) -> Query:
        index = len(self.data_objs)
        self.qstr = self._qstr_constructor(index, '')
        self.md5 = self._md5_hasher()
        print("## qstr", self.qstr)
        return self

    def _request(self) -> bytes:
        response = requests.post(
                f"{self.apihost}query",
                data=self.qstr,
                headers=self.headers
                )
        response.raise_for_status()  # <-- will raise err if not code 200
        return response._content if response._content else b''

    def _query_checker_cacher(self) -> Query:
        response = SVREDIS.get(self.cache_key)  # <-- json str
        if response:
            self.response = response
        else:
            # returns a json encoded string
            response = self._constructor_hasher()._request()
            SVREDIS.set(self.cache_key, response)
            SVREDIS.expire(self.cache_key, TIMEOUT)
            self.response = response
        return self

    def queryset(self) -> Generator[dict, None, None]:
        """Takes response(r), alias_list(al) and returns a generator function
        which is useful in the context manager."""

        al = self.alias_list
        al.insert(0, 'data')
        rd = json.loads(self.response)  # <-- response dict

        def unpack_it(base_dict: dict, unpack_dict: dict) -> dict:
            for k, v in unpack_dict.items():
                base_dict[k] = v
            return base_dict

        def populate_edge(e: dict) -> dict:
            attributes = e.get('attributes', '{}')
            attributes = attributes if attributes else '{}'
            e['attributes'] = json.loads(attributes)
            node = e.pop('node')
            e = unpack_it(e, node)
            document = e.pop('document')
            e = unpack_it(e, json.loads(document))
            return e

        def gener_conn(edges: list) -> Generator[dict, None, None]:
            for e in edges:
                yield populate_edge(e)

        def recur_conn(e: dict, al: list, index: int) -> dict:
            ## the goal is to nest generator functions in the e.dict
            if not index:
                index = len(al) - 1
            if index < 2:
                return e

            nodeConnEdges = e.get(al[index], {}).get('edges', [])
            e[al[index]] = gener_conn(nodeConnEdges)  # <-- make a generator here

            if index == 2:
                return e
            index -= 1
            return recur_conn(e, al, index)

        edges = rd.get(al[0], {}).get(al[1], {}).get('edges', [])
        counter = len(al) - 1

        for e in edges:
            # handles the node
            e = populate_edge(e)
            # handles the nodeConnections
            e = recur_conn(e, al, counter)
            yield e
