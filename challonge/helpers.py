import aiohttp

from . import CHALLONGE_USE_FIELDS_DESCRIPTORS


DEFAULT_TIMEOUT = 30


class ChallongeException(Exception):
    """ If anything goes wrong during the request to the Challonge API,
    this exception will be raised
    """
    pass


class FieldDescriptor:
    def __init__(self, attr):
        self.attr = attr

    def __get__(self, instance, owner):
        return getattr(instance, self.attr)


class FieldHolder(type):
    def _create_holder(self, holder_class, json_def):
        return holder_class(self.connection, json_def)

    def _add_holder(self, local_list, x):
        if x is not None:
            if local_list is None:
                local_list = []
            local_list.append(x)

    def __init__(cls, name, bases, dct):
        super(FieldHolder, cls).__init__(name, bases, dct)
        cls._create_holder = FieldHolder._create_holder
        cls._add_holder = FieldHolder._add_holder
        if CHALLONGE_USE_FIELDS_DESCRIPTORS:
            for a in cls._fields:
                name = '_{}'.format(a)
                setattr(cls, a, FieldDescriptor(name))


class Connection:
    challonge_api_url = 'https://api.challonge.com/v1/{}.json'

    def __init__(self, username: str, api_key: str, timeout, loop):
        self.username = username
        self.api_key = api_key
        self.timeout = timeout
        self.loop = loop

    async def __call__(self, method: str, uri: str, params_prefix: str =None, **params):
        params = self._prepare_params(params, params_prefix)
        # print(params)

        # build the HTTP request and use basic authentication
        url = self.challonge_api_url.format(uri)

        async with aiohttp.ClientSession(loop=self.loop) as session:
            with aiohttp.Timeout(self.timeout):
                auth = aiohttp.BasicAuth(login=self.username, password=self.api_key)
                async with session.request(method, url, params=params, auth=auth) as response:
                    resp = await response.json()
                    if response.status >= 400:
                        raise ChallongeException(uri, params, response.reason)
                    return resp
        return None

    @staticmethod
    def _prepare_params(params, prefix=None) -> dict:
        def val(value):
            if isinstance(value, bool):
                # challonge only accepts lowercase true/false
                value = str(value).lower()
            return str(value)

        new_params = []
        if prefix:
            if prefix.endswith('[]'):
                for k, v in params.items():
                    new_params.extend([('{}[{}]'.format(prefix, k), val(u)) for u in v])
            else:
                new_params = [('{}[{}]'.format(prefix, k), val(v)) for k, v in params.items()]
        else:
            new_params = [(k, val(v)) for k, v in params.items()]
        return new_params


def get_connection(username, api_key, timeout=DEFAULT_TIMEOUT, loop=None):
    return Connection(username, api_key, timeout, loop)


def get_from_dict(s, data, *args):
    for a in args:
        name = '_{}'.format(a) if CHALLONGE_USE_FIELDS_DESCRIPTORS else a
        setattr(s, name, data[a] if a in data else None)


def find_local(local_list, e_id):
    if local_list is not None:
        for e in local_list:
            if e.id == int(e_id):
                return e
    return None