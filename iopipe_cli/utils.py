from . import layers

import boto3


IOPIPE_ARN_PREFIX_TEMPLATE = "arn:aws:lambda:%s:5558675309"
RUNTIME_CONFIG = {
    'nodejs': {
        'Handler': 'node_modules/@iopipe/iopipe/handler'
    },
    'nodejs4.3': {
        'Handler': 'node_modules/@iopipe/iopipe/handler'
    },
    'nodejs6.10': {
        'Handler': 'node_modules/@iopipe/iopipe/handler'
    },
    'nodejs8.10': {
        'Handler': 'node_modules/@iopipe/iopipe/handler'
    },
    'java8': {
        'Handler': {
            'request': 'com.iopipe.generic.GenericAWSRequestHandler',
            'stream': 'com.iopipe.generic.GenericAWSRequestStreamHandler'
        }
    },
    'python2.7': {
        'Handler': 'iopipe.handler.wrapper'
    },
    'python3.0.6': {
        'Handler': 'iopipe.handler.wrapper'
    },
    'python3.7': {
        'Handler': 'iopipe.handler.wrapper',
    }
}


def get_arn_prefix(region):
    return IOPIPE_ARN_PREFIX_TEMPLATE % (get_region(region), )

def get_region(region):
    boto_kwargs = {}
    if region:
        boto_kwargs['region_name'] = region
    session = boto3.session.Session(**boto_kwargs)
    return session.region_name

def get_layers(region, runtime):
    return layers.index(get_region(region), runtime)

def get_lambda_client(region):
    boto_kwargs = {}
    if region:
        boto_kwargs['region_name'] = region
    AwsLambda = boto3.client('lambda', **boto_kwargs)
    return AwsLambda
