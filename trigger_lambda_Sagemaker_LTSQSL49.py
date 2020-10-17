from __future__ import print_function

import base64
import concurrent.futures
import json
import logging
import os
import queue
import time
from concurrent.futures import ThreadPoolExecutor

import boto3
from boto3 import client as boto3_client

##################################################################################################################################################

def feed_the_workers(urls, spacing):
    """ Simulate outside actors sending in work to do, request each url twice """
    for url in urls:
        #time.sleep(spacing)
        q.put(url)
    return "DONE FEEDING"

def process_one_url(executor, payload_one_item):
    """ Process a single item """
    invoke_response = executor.submit(lambda_client.invoke,
                            FunctionName   = "trigger_lambda_Sagemaker49",
                            InvocationType = "RequestResponse",
                            Payload        = json.dumps(payload_one_item)
                        )
    logging.warning('invoke_response value is %s', invoke_response.result()) 
    return invoke_response.result()['Payload'].read().decode("utf-8")

##################################################################################################################################################

q = queue.Queue()

logger = logging.getLogger()
logger.setLevel(logging.INFO)

lambda_client = boto3_client('lambda')

def lambda_handler(event, context):

    
    logging.warning('event value is %s', event)

    try:
        payload = event['body-json']
    except:
        payload = event
        
    logging.warning('payload value is %s', payload)
    
    image_urls = payload['image_urls']
    apollo_opts = payload['apollo_opts'] 
    
    results = []
    results_url_order = []
    
    # We can use a with statement to ensure threads are cleaned up promptly
    with concurrent.futures.ThreadPoolExecutor(max_workers=30) as executor:
    
        # start a future for a thread which sends work in through the queue
        future_to_url = {
            executor.submit(feed_the_workers, image_urls, 0): 'FEEDER DONE'}
    
        while future_to_url:
            # check for status of the futures which are currently working
            done, not_done = concurrent.futures.wait(
                future_to_url, timeout=0.0,
                return_when=concurrent.futures.FIRST_COMPLETED)
    
            # if there is incoming work, start a new future
            while not q.empty():
    
                # fetch a url from the queue
                url = q.get()
                
                payload_one_item = {'image_urls': [url], 'apollo_opts': apollo_opts}
                logging.warning('payload_one_item value is %s', payload_one_item)
    
                # Start the load operation and mark the future with its URL
                future_to_url[executor.submit(process_one_url, executor, payload_one_item)] = payload_one_item
    
            # process any completed futures
            for future in done:
                url = future_to_url[future]
                try:
                    data = future.result()
                    data = json.loads(data)
                    logging.warning('data value is %s', data) 
                    results.append(data)
                    results_url_order.append(url)
                except Exception as exc:
                    print('%r generated an exception: %s' % (url, exc))
                else:
                    if url == 'FEEDER DONE':
                        print(data)
                    else:
                        print('%r page is %d bytes' % (url, len(data)))
    
                # remove the now completed future
                del future_to_url[future]
    
    urls_result_order = []
    for item_in_list in results_url_order:
        urls_result = item_in_list['image_urls']
        urls_result_order.append(urls_result[0])

    order_list_idx = []
    for item_in_list in urls_result_order:
        order_list_idx.append(image_urls.index(item_in_list))
    
    logging.warning('image_urls value is %s', image_urls) 
    logging.warning('results_url_order value is %s', results_url_order) 
    logging.warning('order_list_idx value is %s', order_list_idx)
    
    results_ordered = [x for _,x in sorted(zip(order_list_idx,results))]
    
    logging.warning('results value is %s', results) 
    logging.warning('results_ordered value is %s', results_ordered) 
    
    return results_ordered
