# A suite of integrations tests for the Tapis Python SDK.
# Build the test docker image: docker build -t tapis/pysdk-tests -f Dockerfile-tests .
# Run these tests using the built docker image: docker run -it --rm  tapis/pysdk-tests

import pytest

from common.config import conf
from tapy.dyna import DynaTapy
from tapy.dyna.dynatapy import TapisResult

@pytest.fixture
def client():
    base_url = getattr(conf, 'base_url', 'https://dev.develop.tapis.io')
    username = getattr(conf, 'username', 'pysdk')
    account_type = getattr(conf, 'account_type', 'service')
    tenant_id = getattr(conf, 'tenant_id', 'dev')
    t = DynaTapy(base_url=base_url, username=username, account_type=account_type, tenant_id=tenant_id)
    t.get_tokens()
    return t


# -----------------------------------------------------
# Tests to check parsing of different result structures -
# -----------------------------------------------------
def test_tapisresult_list_simple():
    result = ['a',  1, 'b', True, None, 3.14159, b'some bytes']
    tr = TapisResult(result)
    r = tr.result
    assert len(r) == 7
    assert r[0] == 'a'
    assert r[1] == 1
    assert r[2] == 'b'
    assert r[3] == True
    assert r[4] == None
    assert r[5] == 3.14159
    assert r[6] == b'some bytes'

def test_tapisresult_dict():
    result = {'a': 1, 'b': 'bee', 'c': b'bytes', 'd': True, 'e': 3.14159, 'f': None}
    tr = TapisResult(**result)
    assert tr.a == 1
    assert tr.b == 'bee'
    assert tr.c == b'bytes'
    assert tr.d is True
    assert tr.e == 3.14159
    assert tr.f is None

def test_tapisresult_list_o_dict():
    result = [{'a': 1, 'b': 'bee', 'c': b'bytes', 'd': True, 'e': 3.14159, 'f': None},
              {'a': 10, 'b': 'foo', 'c': b'bytes', 'd': False, 'e': 3.14159, 'f': None},
              ]
    tr_list = [TapisResult(**r) for r in result]
    assert len(tr_list) == 2
    # first item -
    tr_1 = tr_list[0]
    assert tr_1.a == 1
    assert tr_1.b == 'bee'
    assert tr_1.c == b'bytes'
    assert tr_1.d is True
    assert tr_1.e == 3.14159
    assert tr_1.f is None
    # 2nd item -
    tr_2 = tr_list[1]
    assert tr_2.a == 10
    assert tr_2.b == 'foo'
    assert tr_2.c == b'bytes'
    assert tr_2.d is False
    assert tr_2.e == 3.14159
    assert tr_2.f is None

def test_tapisresult_nested_dicts():
    result = [{'a': [{'bb': 10, 'cc': True}, {'dd': 5}],
               'b': [{'ee': b'bytes'}] },
              {'time_1': [{'x_0': 'abc', 'x_1': 'def'}, {'y_0': 0, 'y_1': 3.14}]}
              ]
    tr_list = [TapisResult(**r) for r in result]
    assert len(tr_list) == 2
    # first item -
    tr_1 = tr_list[0]
    assert type(tr_1.a) == list
    assert tr_1.a[0].bb == 10
    assert tr_1.a[0].cc is True
    assert tr_1.a[1].dd == 5

    # 2nd item -
    tr_2 = tr_list[1]
    assert type(tr_2.time_1) == list
    assert tr_2.time_1[0].x_0 == 'abc'
    assert tr_2.time_1[0].x_1 == 'def'
    assert tr_2.time_1[1].y_0 == 0
    assert tr_2.time_1[1].y_1 == 3.14


# ----------------
# tokens API tests -
# ----------------

def test_client_has_tokens(client):
    # the fixture should have already created tokens on the client.
    # the access token object
    assert hasattr(client, 'access_token')
    access_token = client.access_token
    # the actual JWT
    assert hasattr(access_token, 'access_token')
    # the expiry fields
    assert hasattr(access_token, 'expires_at')
    assert hasattr(access_token, 'expires_in')

    # the refresh token object
    assert hasattr(client, 'refresh_token')
    # the actual JWT -
    refresh_token = client.refresh_token
    # the expiry fields
    assert hasattr(refresh_token, 'expires_at')
    assert hasattr(refresh_token, 'expires_in')


def test_create_token(client):
    toks = client.tokens.create_token(token_username='pysdk',
                                      token_tenant_id='dev',
                                      account_type='service',
                                      access_token_ttl=14400,
                                      generate_refresh_token=True,
                                      refresh_token_ttl=9999999)
    assert hasattr(toks, 'access_token')
    access_token= toks.access_token
    assert hasattr(access_token, 'access_token')
    assert hasattr(access_token, 'expires_at')
    assert hasattr(access_token, 'expires_in')

    assert hasattr(toks, 'refresh_token')
    refresh_token= toks.refresh_token
    assert hasattr(refresh_token, 'refresh_token')
    assert hasattr(refresh_token, 'expires_at')
    assert hasattr(refresh_token, 'expires_in')


# -----------------
# tenants API tests -
# -----------------

def test_list_tenants(client):
    tenants = client.tenants.list_tenants()
    for t in tenants:
        assert hasattr(t, 'base_url')
        assert hasattr(t, 'tenant_id')
        assert hasattr(t, 'public_key')
        assert hasattr(t, 'is_owned_by_associate_site')
        assert hasattr(t, 'token_service')
        assert hasattr(t, 'security_kernel')

def test_get_tenant_by_id(client):
    t = client.tenants.get_tenant(tenant_id='dev')
    assert t.base_url == 'https://dev.develop.tapis.io'
    assert t.tenant_id == 'dev'
    assert t.public_key.startswith('-----BEGIN PUBLIC KEY-----')
    assert t.is_owned_by_associate_site == True
    assert t.token_service == 'https://dev.develop.tapis.io/v3/tokens'
    assert t.security_kernel == 'https://dev.develop.tapis.io/v3/security'

def test_list_owners(client):
    owners = client.tenants.list_owners()
    for o in owners:
        assert hasattr(o, 'create_time')
        assert hasattr(o, 'email')
        assert hasattr(o, 'last_update_time')
        assert hasattr(o, 'name')

def test_get_owners(client):
    owner = client.tenants.get_owner(email='jstubbs@tacc.utexas.edu')
    assert owner.email == 'jstubbs@tacc.utexas.edu'
    assert owner.name == 'Joe Stubbs'