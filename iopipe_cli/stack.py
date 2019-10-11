import boto3
import itertools
import json

from . import awslambda, utils
from .combine_dict import combine_dict


def get_stack_ids():
    CloudFormation = boto3.client("cloudformation")

    def stack_filter(stack_id):
        resources = CloudFormation.list_stack_resources(StackName=stack_id)
        for resource in resources["StackResourceSummaries"]:
            if resource["ResourceType"] == "LambdaResourceType-PLACEHOLDER":
                return True

    def map_stack_ids():
        for stack in stacks["StackSummaries"]:
            return stack["StackId"]

    token = None
    stack_id_pages = []
    while True:
        stacks = CloudFormation.list_stacks(NextToken=token)
        stack_id_pages += map(map_stack_ids, stacks)
        token = stacks["NextToken"]
        if not token:
            break
    return filter(stack_filter, itertools.chain(*stack_id_pages))


def get_template(stackid):
    CloudFormation = boto3.client("cloudformation")
    # DOC get_template:
    # https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/cloudformation.html#CloudFormation.Client.get_template
    template_body = CloudFormation.get_template(StackName=stackid)
    #    example_get_template_body = '''
    #    {
    #    'TemplateBody': {},
    #    'StagesAvailable': [
    #        'Original'|'Processed',
    #    ]
    #    }
    #    '''
    return template_body  # apply_function_cloudformation(template_body)


def modify_cloudformation(template_body, function_arn, token):
    ##runtime = info.get('Configuration', {}).get('Runtime', '')
    ##orig_handler = info.get('Configuration', {}).get('Handler', '')
    func_template = template_body.get("Resources", {}).get(function_arn, {})
    orig_handler = func_template.get("Properties", {}).get("Handler", None)
    runtime = func_template.get("Properties", {}).get("Runtime", None)
    runtime_handler = utils.RUNTIME_CONFIG.get(runtime, {}).get("Handler", None)

    if runtime == "provider" or runtime not in utils.RUNTIME_CONFIG.keys():
        raise awslambda.UpdateLambdaException(
            "Unsupported Lambda runtime: %s" % (runtime,)
        )
    if orig_handler == runtime_handler:
        raise awslambda.UpdateLambdaException("Already configured.")

    updates = {
        "Resources": {
            function_arn: {
                "Properties": {"Handler": runtime_handler},
                "Environment": {
                    "Variables": {"IOPIPE_HANDLER": orig_handler, "IOPIPE_TOKEN": token}
                },
            }
        }
    }
    # context = DeepChainMap({}, updates, template_body)
    context = combine_dict(template_body, updates)
    return context


def update_cloudformation_file(filename, function_arn, output, token):
    # input options to support:
    # - cloudformation template file (json and yaml)
    # - cloudformation stack (deployed on AWS)
    # - SAM file
    # - Serverless.yml
    orig_template_body = ""
    with open(filename) as yml:
        orig_template_body = json.loads(yml.read())
    cf_template = modify_cloudformation(orig_template_body, function_arn, token)
    if output == "-":
        print(json.dumps(cf_template, indent=2))
    else:
        with open(output, "w") as yml:
            yml.write(json.dumps(cf_template, indent=2))


def update_cloudformation_stack(stack_id, function_arn, token):
    CloudFormation = boto3.client("cloudformation")

    # stackid = get_stack_ids(function_arn)
    orig_template = get_template(stack_id)
    template_body = modify_cloudformation(orig_template, function_arn, token)
    # DOC update_stack:
    # https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/cloudformation.html#CloudFormation.Client.update_stack
    CloudFormation.update_stack(StackName=stack_id, TemplateBody=template_body)
