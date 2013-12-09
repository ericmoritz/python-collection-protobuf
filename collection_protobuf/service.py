"""
This provides an abstract service class for services 
implementing a collection+protobuf service
"""
from abc import ABCMeta, abstractmethod, abstractproperty
from contextlib import contextmanager
import logging

log = logging.getLogger(__name__)

def trace(val):
    log.debug("{!r}".format(val))
    return val


class ItemHooks(object):
    def __init__(self):
        self.hooks = []

    def do(self, item, value):
        for hook in self.hooks:
            hook(item, value)

    def add(self, hook):
        self.hooks.append(hook)


class Error(Exception):
    def __init__(self, status, title="", code="", message=""):
        self.status = status
        self.title = title
        self.code = code
        self.message = message

    def _set_error(self, resource):
        """
        Set the error message of a resource
        """
        error = resource.collection.error
        error.title = title
        error.code = code
        error.message = message


class Result(object):
    def __init__(self, status, resource):
        self.status = status
        self.resource = resource


@contextmanager
def result_manager(status, resource):
    result = Result(status, resource)
    try:
        yield result
    except Error, err:
        msg = result.resource.collection.error
        msg.title = err.title
        msg.code = err.code
        msg.message = err.message
        result.status = err.status
    except Exception, e:
        msg = result.resource.collection.error
        msg.title = "Internal Server Error"
        msg.code = "500"
        msg.message = "The server have encountered an error, please wait and try again."
        result.status = 500
        log.exception("Error creating result")


class Service(object):
    __metaclass__ = ABCMeta

    def __init__(self, *args, **kwargs):
        super(Service, self).__init__(*args, **kwargs)
        self.item_hooks = ItemHooks()

    ###================================================================
    ### Public API
    ###================================================================
    def query(self, *args, **kwargs):
        """
        query(self, *args, **kwargs) -> Result()

        Query the service and return a Result()
        """
        with result_manager(200, self._resource_pb()) as result:
            self.__query(result, *args, **kwargs)
        return result

    def store_bytes(self, byte_string):
        with result_manager(200, self._resource_pb()) as result:
            self.__store(result, 
                         self.__parse_collection(result, byte_string).template)
        return result

    def store(self, template_collection):
        """
        store(self, template_collection) -> Result()

        Store template into
        """
        with result_manager(200, self._resource_pb()) as result:
            self.__store(result, template_collection.template)
        return result

    def delete(self, *args, **kwargs):
        """
        delete(self, item) -> Result()
        """
        with result_manager(204, None) as result:
            if not self._delete(*args, **kwargs):
                result.status = 404
        return result


    ###================================================================
    ### Abstract properties and methods
    ###================================================================
    @abstractmethod
    def _ResourcePB(self):
        """
        ResourcePB() -> protobuf.message.Message()

        Return a protobuf message that is shaped like the Resource
        message as defined by the collection+protobuf specification
        """

    @abstractmethod
    def _query(self, *args, **kwargs):
        """
        _query(self, *args, **kwargs) -> iterator(value())

        Return an iterator for the items of this collection.

        Return None if the query results are not found.
        """
        
    @abstractmethod
    def _validate_template(self, template):
        """
        _validate_template(self, template) -> value()
        
        convert the template into a value that will be passed to self._save()

        raise a service.Error() on failed validation
        """

    @abstractmethod
    def _save(self, value):
        """
        _save(self, value()) -> int()

        Return an HTTP status code which conveys what the save did

        201 Created    - Inserted
        200 Ok         - Updated
        
        Raise a service.Error() if an error occured
        """
        pass

    @abstractmethod
    def _delete(self, item):
        """
        item(self, Message()) -> bool()

        True if delete occured
        False if not delete occured
        """

    @abstractmethod
    def _item(self, item, value):
        """
        item(self, Message(), value()) -> Message()

        Called for each value() in the iterator returned by self._query()
        Called for the value() returned by _validate_template()
        """

    def _resource_pb(self):
        """
        Used to configure the resource message
        """
        return self._ResourcePB()

    ###================================================================
    ### Internal
    ###================================================================
    def __save_template(self, result, template):
        value = self._validate_template(template)
        result.status = self._save(value)

    def __update_template(self, resource, template):
        resource.collection.template.CopyFrom(template)

    def __store(self, result, template):
        # Put the template into the collection in case 
        # validate or save raise a service.Error()
        self.__update_template(result.resource, template)
        item = self.__save_template(result, template)
        return result

    def __parse_collection(self, result, byte_string):
        collection = result.resource.collection
        try:
            collection.ParseFromString(byte_string)
            return collection
        except Exception, e:
            raise Error(
                400,
                title="Error parsing body",
                code="400",
                message=unicode(e))

    def __query(self, result, *args, **kwargs):
        value_iter = self._query(*args, **kwargs)
        if value_iter is None:
            raise Error(404, title="Not Found", code="404", message="resource not found")
        self.__process_items(result.resource, value_iter)
        return result

    def __process_items(self, resource, items):
        for item in items:
            self.__add_item(resource, item)
        return resource

    def __add_item(self, resource, value):
        item = resource.collection.items.add()
        self._item(item, value)
        self.item_hooks.do(item, value)
    
