try:
  import unzip_requirements
except ImportError:
  pass

import base64
import csv
import io
import json
import logging
import os
import subprocess

import boto3
import google.protobuf.json_format as json_format
from google.protobuf.json_format import MessageToJson
from google.protobuf.message import DecodeError
from PIL import Image
from tensorflow.core.framework import \
    tensor_pb2  # pylint: disable=no-name-in-module
from tensorflow.python.framework import \
    tensor_util  # pylint: disable=no-name-in-module
from tensorflow.python.saved_model.saved_model import signature_constants

import classification_pb2

#from tensorflow.predictor import tf_serializer as tf_protobuf_serializer
#from sagemaker.tensorflow.predictor import tf_deserializer as tf_protobuf_deserializer
#from tensorflow_serving.apis import classification_pb2


try:
    from urllib2 import urlopen
    from urllib2 import HTTPError
except ImportError:
    from urllib.request import urlopen
    from urllib.error import HTTPError
    import urllib


##################################################################################################################################################


CONTENT_TYPE_JSON = 'application/json'
CONTENT_TYPE_CSV = 'text/csv'
CONTENT_TYPE_OCTET_STREAM = 'application/octet-stream'
CONTENT_TYPE_NPY = 'application/x-npy'


REGRESSION_REQUEST = 'RegressionRequest'
MULTI_INFERENCE_REQUEST = 'MultiInferenceRequest'
CLASSIFICATION_REQUEST = 'ClassificationRequest'
PREDICT_REQUEST = 'PredictRequest'


class _TFProtobufSerializer(object):
    def __init__(self):
        self.content_type = CONTENT_TYPE_OCTET_STREAM

    def __call__(self, data):
        # isinstance does not work here because a same protobuf message can be imported from a different module.
        # for example sagemaker.tensorflow.tensorflow_serving.regression_pb2 and tensorflow_serving.apis.regression_pb2
        predict_type = data.__class__.__name__

        available_requests = [PREDICT_REQUEST, CLASSIFICATION_REQUEST, MULTI_INFERENCE_REQUEST, REGRESSION_REQUEST]

        if predict_type not in available_requests:
            raise ValueError('request type {} is not supported'.format(predict_type))
        return data.SerializeToString()


tf_serializer = _TFProtobufSerializer()


class _TFProtobufDeserializer(object):
    def __init__(self):
        self.accept = CONTENT_TYPE_OCTET_STREAM

    def __call__(self, stream, content_type):
        try:
            data = stream.read()
        finally:
            stream.close()

        for possible_response in _POSSIBLE_RESPONSES:
            try:
                response = possible_response()
                response.ParseFromString(data)
                return response
            except (UnicodeDecodeError, DecodeError):
                # given that the payload does not have the response type, there no way to infer
                # the response without keeping state, so I'm iterating all the options.
                pass
        raise ValueError('data is not in the expected format')


class _TFJsonSerializer(object):
    def __init__(self):
        self.content_type = CONTENT_TYPE_JSON

    def __call__(self, data):
        if isinstance(data, tensor_pb2.TensorProto):
            return json_format.MessageToJson(data)
        else:
            return json_serializer(data)


tf_json_serializer = _TFJsonSerializer()

##################################################################################################################################################

def convert_image(data, size):
    if size is not None:
        image = Image.open(io.BytesIO(data))
        image = image.resize(size, Image.BILINEAR)

        imgByteArr = io.BytesIO()
        image.save(imgByteArr, format='JPEG', quality=100)
        data = imgByteArr.getvalue()
    return data

def load_images(urls):
    logger = logging.getLogger(__name__)
    for url in urls:
        #apollo_url = ';'.join([url, apollo_opts])
        apollo_url = url
        logging.warning('apollo_url is %s', apollo_url)

        try:
            #data = urlopen(apollo_url, data=None, timeout=10).read()
            req = urllib.request.Request(apollo_url)
            response = urllib.request.urlopen(req)
            data = response.read()                      
            size = 299, 299
            data = convert_image(data, size)
        except HTTPError as e:
            logger.warn(e.msg + '. Image probably not from Apollo.')
            logger.info('Re-downloading from {}...'.format(url))
            data = urlopen(url, data=None, timeout=10).read()
            size = 299, 299
            data = convert_image(data, size)
        yield data

def create_image_classification_request(
        files,
        model_name='generic_model',
        feature_name='image/encoded',
        signature_name=signature_constants.DEFAULT_SERVING_SIGNATURE_DEF_KEY):
    request = classification_pb2.ClassificationRequest()
    request.model_spec.name = model_name
    request.model_spec.signature_name = signature_name
    for data in files:
        example = request.input.example_list.examples.add()
        example.features.feature[feature_name].bytes_list.value.extend([data])
    return request
    


##################################################################################################################################################

logger = logging.getLogger()
logger.setLevel(logging.INFO)


# grab environment variables
ENDPOINT_NAME = os.environ['ENDPOINT_NAME']
runtime = boto3.client('runtime.sagemaker')

def inferHandler(event, context):

    logging.warning('endpoint name is %s', ENDPOINT_NAME)
    logging.warning('event value is %s', event)
    
    try:
        payload = event['body-json']
        logging.warning('payload value is %s', payload)
    except:
        payload = event
        logging.warning('payload value is %s', payload)
  
    for key, value in payload.items():
      print(key, value)
    
    body = payload['body']
    logging.warning('body value is %s', body)
    
    body_dict = json.loads(body)
    logging.warning('body_dict value is %s', body_dict)
    
    image_urls = body_dict['image_urls'] 
    apollo_opts = body_dict['apollo_opts'] 
    
    logging.warning('image_urls value is %s', image_urls)
    logging.warning('apollo_opts value is %s', apollo_opts)
    
    request_images = create_image_classification_request(load_images(image_urls))
    payload_protobuf = tf_serializer(request_images)
    
    json_response = runtime.invoke_endpoint(EndpointName=ENDPOINT_NAME,
                                       ContentType='application/octet-stream',
                                       Body=payload_protobuf)
    
    predictions_proto = json_response['Body'].read()
    predictions_json = json.loads(predictions_proto.decode('utf-8'))
    #predictions_final = predictions_json['result']['classifications'][0]['classes']
    predictions_final = predictions_json['result']['classifications']
    
    logging.warning('predictions_final value is %s', predictions_final) 
    
    return {
        'statusCode': 200,
        'headers': { 'Content-Type': 'application/json' },
        'body': json.dumps(predictions_final)
    }
    
