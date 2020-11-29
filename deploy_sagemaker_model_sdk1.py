# Deploy the Car Parts Classifier

## Tutorial
#In order to deploy a Keras model, such as the Car Parts Classifier, we need to first convert it to TensorFlow's SavedModel format. The code to do that is in `export_keras_model.py`. Check that file's comments for details.

# Once the model is in TensorFlow SavedModel format, it needs to be put in this directory structure: `export/Servo/<version_number>` and then the entire directory needs to be compressed in a `.tar.gz` file and uploaded in S3. The code to do that is again in `export_keras_model.py`, where you can find an example workflow.

# Now that the model is in S3, we need to specify how TensorFlow Serving can take the inputs. This is done in `entry_point.py`. Check that file for more details.

#Once that is done, we can begin deploying the model! 


## Deployment

# Let's instantiate the model from S3, with the entry point specified in `entry_point.py`. This tells TensorFlow Serving how to call the model.

#!pip install "sagemaker<2"

from sagemaker import get_execution_role
from sagemaker.tensorflow.model import TensorFlowModel

import boto3

MODEL_VERSION = 1
MODEL_NAME = 'CarPartsClassifierV{}'.format(MODEL_VERSION)

#role = get_execution_role()

model_path = 's3://sagemaker-models-euwest2/inception_resnetv2_nainet49_v1.tar.gz'

def resolve_sm_role():
    client = boto3.client('iam', region_name='eu-west-1')
    response_roles = client.list_roles(
        PathPrefix='/',
        MaxItems=999
    )
    for role in response_roles['Roles']:
        if role['RoleName'].startswith('AmazonSageMaker-ExecutionRole-'):
            print('Resolved SageMaker IAM Role to: ' + str(role))
            return role['Arn']
    raise Exception('Could not resolve what should be the SageMaker role to be used')

role = resolve_sm_role()
                     
sagemaker_model = TensorFlowModel(
    model_data=model_path,
    role=role,
    entry_point='entry_point.py',
    name=MODEL_NAME)
    
try:
    client = boto3.client('sagemaker')
    client.delete_endpoint(EndpointName=MODEL_NAME)
    client.delete_model(ModelName=MODEL_NAME)
except:
    pass
    
sagemaker_model.deploy(initial_instance_count=1, instance_type='ml.m4.xlarge')


