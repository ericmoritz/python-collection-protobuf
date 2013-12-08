test:
	pip install protobuf pytest pytest-quickcheck
	protoc --python_out=tests/ --proto_path=tests/ tests/*.proto
	py.test 
