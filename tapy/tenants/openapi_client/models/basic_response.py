# coding: utf-8

"""
    Tenants API

    Manage Tapis Tenants.  # noqa: E501

    The version of the OpenAPI document: 1
    Contact: cicsupport@tacc.utexas.edu
    Generated by: https://openapi-generator.tech
"""


import pprint
import re  # noqa: F401

import six


class BasicResponse(object):
    """NOTE: This class is auto generated by OpenAPI Generator.
    Ref: https://openapi-generator.tech

    Do not edit the class manually.
    """

    """
    Attributes:
      openapi_types (dict): The key is attribute name
                            and the value is attribute type.
      attribute_map (dict): The key is attribute name
                            and the value is json key in definition.
    """
    openapi_types = {
        'version': 'str',
        'message': 'str',
        'status': 'str'
    }

    attribute_map = {
        'version': 'version',
        'message': 'message',
        'status': 'status'
    }

    def __init__(self, version=None, message=None, status=None):  # noqa: E501
        """BasicResponse - a model defined in OpenAPI"""  # noqa: E501

        self._version = None
        self._message = None
        self._status = None
        self.discriminator = None

        if version is not None:
            self.version = version
        if message is not None:
            self.message = message
        if status is not None:
            self.status = status

    @property
    def version(self):
        """Gets the version of this BasicResponse.  # noqa: E501

        Version of the API  # noqa: E501

        :return: The version of this BasicResponse.  # noqa: E501
        :rtype: str
        """
        return self._version

    @version.setter
    def version(self, version):
        """Sets the version of this BasicResponse.

        Version of the API  # noqa: E501

        :param version: The version of this BasicResponse.  # noqa: E501
        :type: str
        """

        self._version = version

    @property
    def message(self):
        """Gets the message of this BasicResponse.  # noqa: E501

        Brief description of the response  # noqa: E501

        :return: The message of this BasicResponse.  # noqa: E501
        :rtype: str
        """
        return self._message

    @message.setter
    def message(self, message):
        """Sets the message of this BasicResponse.

        Brief description of the response  # noqa: E501

        :param message: The message of this BasicResponse.  # noqa: E501
        :type: str
        """

        self._message = message

    @property
    def status(self):
        """Gets the status of this BasicResponse.  # noqa: E501

        Whether the request was a success or failure.  # noqa: E501

        :return: The status of this BasicResponse.  # noqa: E501
        :rtype: str
        """
        return self._status

    @status.setter
    def status(self, status):
        """Sets the status of this BasicResponse.

        Whether the request was a success or failure.  # noqa: E501

        :param status: The status of this BasicResponse.  # noqa: E501
        :type: str
        """
        allowed_values = ["success", "failure"]  # noqa: E501
        if status not in allowed_values:
            raise ValueError(
                "Invalid value for `status` ({0}), must be one of {1}"  # noqa: E501
                .format(status, allowed_values)
            )

        self._status = status

    def to_dict(self):
        """Returns the model properties as a dict"""
        result = {}

        for attr, _ in six.iteritems(self.openapi_types):
            value = getattr(self, attr)
            if isinstance(value, list):
                result[attr] = list(map(
                    lambda x: x.to_dict() if hasattr(x, "to_dict") else x,
                    value
                ))
            elif hasattr(value, "to_dict"):
                result[attr] = value.to_dict()
            elif isinstance(value, dict):
                result[attr] = dict(map(
                    lambda item: (item[0], item[1].to_dict())
                    if hasattr(item[1], "to_dict") else item,
                    value.items()
                ))
            else:
                result[attr] = value

        return result

    def to_str(self):
        """Returns the string representation of the model"""
        return pprint.pformat(self.to_dict())

    def __repr__(self):
        """For `print` and `pprint`"""
        return self.to_str()

    def __eq__(self, other):
        """Returns true if both objects are equal"""
        if not isinstance(other, BasicResponse):
            return False

        return self.__dict__ == other.__dict__

    def __ne__(self, other):
        """Returns true if both objects are not equal"""
        return not self == other
