from collection_protobuf import service
import pytest
import test_pb2
import logging
logging.basicConfig(level=logging.DEBUG)


class TestService(service.Service):
    _ResourcePB = test_pb2.TestResource

    def __init__(self):
        self.__data = {}


    def _query(self, key=None):
        if key is not None and key in self.__data:
            return [(key, self.__data[key])]
        elif key is None:
            return self.__data.iteritems()

    def _validate_template(self, template):
        if template.pb.key:
            return (template.pb.key, template.pb.value)
        else:
            raise service.Error(
                400,
                title="Missing Key")

    def _save(self, record):
        key, value = record
        exists = key in self.__data
        self.__data[key] = value
        return 200 if exists else 201
    
    def _delete(self, item):
        if item.pb.key in self.__data:
            del self.__data[item.pb.key]
            return True
        else:
            return False

    def _item(self, item, record):
        key, value = record
        item.pb.key = key
        item.pb.value = value
        return item


class Model(object):
    def __init__(self):
        self.data = {}

    def store(self, collection_template):
        template = collection_template.template
        if template.pb.key:
            status = 200 if template.pb.key in self.data else 201
            self.data[template.pb.key] = template.pb.value
            return status
        else:
            return 400

    def delete(self, key):
        if key in self.data:
            del self.data[key]
            return 204
        else:
            return 404

    def query(self, key=None):
        if key is None:
            return self.data.items()
        else:
            return self.data.get(key)

    

service_obj = TestService()
model = Model()

def assert_model():
    # Assert that all the items are in the model
    result = service_obj.query()
    for item in result.resource.collection.items:
        assert model.data[item.pb.key] == item.pb.value

    # Assert that all the items in the model are in the service
    for key, value in model.data.iteritems():
        result = service_obj.query(key)
        assert result.resource.collection.items[0].pb.value == value
    
def assert_status(result, status):
    assert status == result.status

@pytest.mark.randomize(key=str, value=str, null_key=bool)
def test_store(key, value, null_key):
    collection = make_template(key, value, null_key)
    result = service_obj.store(collection)
    status = model.store(collection)
    assert_status(result, status)
    assert_model()


@pytest.mark.randomize(key=str, value=str, null_key=bool)
def test_store_bytes(key, value, null_key):
    collection = make_template(key, value, null_key)
    byte_string = collection.SerializeToString()
    result = service_obj.store_bytes(byte_string)
    status = model.store(collection)
    assert_status(result, status)
    assert_model()

@pytest.mark.randomize(i=int)
def test_delete(i):
    keys = model.data.keys()
    key = keys[i % len(keys)]
    item = service_obj._ResourcePB().collection.items.add()
    item.pb.key = key
    
    result = service_obj.delete(item)
    status = model.delete(key)
    assert_status(result, status)
    assert_model()

    result = service_obj.delete(item)
    status = model.delete(key)
    assert_status(result, status)
    assert_model()


def make_template(key, value, null_key):
    collection = service_obj._ResourcePB().collection
    template = collection.template
    template.pb.key = "" if null_key else key
    template.pb.value = value 
    return collection
