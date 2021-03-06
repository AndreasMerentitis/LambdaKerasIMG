# Serverless Machine Learning on AWS Lambda with TensorFlow (ResNet model)

Configured to deploy a trained image TensorFlow model to AWS Lambda using the Serverless framework
and AWS Sagemaker for deploying the endpoint. The model is a pretrained ResNet. 

### Prerequisites

#### Setup serverless

```  
sudo npm install -g serverless

sudo serverless plugin install -n serverless-python-requirements

pip install -r requirements.txt

```
#### Setup AWS credentials

Make sure you have the AWS access key and secrete keys setup locally, following this video [here](https://www.youtube.com/watch?v=KngM5bfpttA)

### Download the code locally

```  
serverless create --template-url https://github.com/AndreasMerentitis/LambdaKerasIMG --path tf-lambda
```

### Update S3 bucket to unique name
In serverless.yml:
```  
  environment:
    BUCKET: <your_unique_bucket_name> 
```

### Check the file syntax for any files changed 
```
pyflakes infer.py

```
We can ignore the warning about not using 'unzip_requirements' as its needed to set the requirements for lamda

### Copy the model artifact to the designed S3 bucket
From local drive:
```  
aws s3 cp inception_resnetv2_nainet49_v1.tar.gz s3://serverless-ml-2/ --grants read=uri=http://acs.amazonaws.com/groups/global/AllUsers
```

Or from an S3 bucket:
```  
aws s3 cp s3://sagemaker-models-euwest2/inception_resnetv2_nainet49_v1.tar.gz s3://serverless-ml-2/ --grants read=uri=http://acs.amazonaws.com/groups/global/AllUsers
```

### Deploy to the cloud  
```
cd tf-lambda

npm install

python deploy_sagemaker_model_sdk1.py

sudo serverless deploy --stage dev

curl -vX POST -H 'Content-Type: application/json' -d @urls.json https://oz5xe30lrj.execute-api.eu-west-1.amazonaws.com/dev/infer
```


### Compare single-threaded vs multi-threaded performance
```
In order to optimize performance a multithreaded inference API was created as well. To compare the two: 

time curl -vX POST -H 'Content-Type: application/json' -d @urls.json https://4rj3voj7m8.execute-api.eu-west-1.amazonaws.com/dev/infer

time curl -vX POST -H 'Content-Type: application/json' -d @urls.json https://4rj3voj7m8.execute-api.eu-west-1.amazonaws.com/dev/inferqueue
```


### Clean up (remove deployment) 
```
aws s3 rm s3://serverless-ml-2 --recursive

python remove_sagemaker_model_sdk1.py

sudo serverless remove --stage dev 
```

# Using data and extending the basic idea from these sources:
* https://github.com/mikepm35/TfLambdaDemo
* https://medium.com/@mike.p.moritz/running-tensorflow-on-aws-lambda-using-serverless-5acf20e00033
* https://www.serverless.com/blog/using-tensorflow-serverless-framework-deep-learning-image-recognition
* https://aws.amazon.com/blogs/machine-learning/how-to-deploy-deep-learning-models-with-aws-lambda-and-tensorflow/










