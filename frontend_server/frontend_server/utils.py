from storages.backends.s3boto import S3BotoStorage


def StaticRootS3BotoStorage():
    return S3BotoStorage(location="static")


def MediaRootS3BotoStorage():
    return S3BotoStorage(location="media")
