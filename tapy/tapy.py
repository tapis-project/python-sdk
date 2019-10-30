from tenants import openapi_client as tenants_client
from tokens import openapi_client as tokens_client

import errors

class Tapis(object):
    """
    Public class for interacting with a Tapis v3 instance.
    """
    def __init__(self,
                 tenant_id=None,
                 base_url=None,
                 session_id=None,
                 ):
        if len([x for x in (tenant_id, base_url, session_id) if not x is None]) > 1:
            raise errors.TapyClientConfigurationError(msg='Invalid arguments; only one of '
                                                          'tenant_id, base_url, session_id should be passed.')
        if tenant_id:
            raise errors.TapyClientNotImplementedError(msg='tenant_id argument not supported yet.')
        if session_id:
            raise errors.TapyClientNotImplementedError(msg='session_id argument not supported yet.')

        self.tenant_id = tenant_id
        self.base_url = base_url
        self.session_id = session_id
        if self.session_id:
            self._restore_from_session(session_id)
        else:
            self.session_id = self._get_new_session_id()
        self._instantiate_oa_clients()

    def _restore_from_session(self, session):
        """
        Restore the authentication context from a previous session.
        :param session:
        :return:
        """
        # todo -
        pass

    def _get_new_session_id(self):
        """
        Generate a new session id for this session.
        :return:
        """
        #todo -
        return 'abc'

    def _instantiate_oa_clients(self):
        """
        Instantiate the necessary openapi client objects for each service.
        :return:
        """
        config = tenants_client.Configuration()
        config.host = self.base_url
        self.tenants = tenants_client.TenantsApi(config)

        config = tokens_client.Configuration()
        config.host = self.base_url
        self.tokens = tokens_client.TokensApi(config)
