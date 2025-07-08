import boto3

session = boto3.Session()
sts = session.client("sts")
identity = sts.get_caller_identity()
print("AWS Identity:", identity)
