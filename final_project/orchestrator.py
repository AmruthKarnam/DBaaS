from flask import Flask, render_template, jsonify, request, abort, g,request
import requests
#import status
from werkzeug.exceptions import BadRequest
#from models import sessions
app = Flask(__name__)
from sqlalchemy import create_engine, Sequence
from sqlalchemy import String, Integer, Float, Boolean, Column, ForeignKey, DateTime
from sqlalchemy.orm import sessionmaker
from kazoo.exceptions import ConnectionLossException
from kazoo.exceptions import NoAuthException
import random
from kazoo.exceptions import ConnectionLossException
from kazoo.exceptions import NoAuthException
from datetime import datetime
from multiprocessing import Value
import time
import csv
import json
import pika
import sys
import uuid
import threading
import math
with open("/code/queries.txt","w") as f: pass
import docker
from kazoo.client import KazooClient
import sys
counter = Value('i', 0)
counter1 = Value('i',0)
connection = pika.BlockingConnection(
pika.ConnectionParameters(host='rabbitmq',heartbeat=0))
channel = connection.channel()
client1 = docker.APIClient(base_url='unix://var/run/docker.sock')
client = docker.DockerClient(base_url='unix://var/run/docker.sock')
count=0
flagrem=0
countZookeeper=0
zk = KazooClient(hosts='zookeeper:2181')
zk.start()
zk.ensure_path("/zookeeper")
@zk.ChildrenWatch('/zookeeper')
def cont_watch(event):
    print("inside watch")
    global flagrem

    children_list = zk.get_children("/zookeeper")
    if 'quota' in children_list :
        children_list.remove('quota')
    if 'config' in children_list :
        children_list.remove('config')
    print(children_list)
    print("flagrem",flagrem)
    if(flagrem==1):
        print(len(children_list))
        createContainer(len(children_list))
        flagrem=0   
    print("flagrem now",flagrem,len(children_list))

def createContainer(containers):
    with counter1.get_lock():
        
        count = len(client.containers.list()) + 1
        varname="slave"+str(count)
        print("new slave name created",varname)
        print(count,"count of container")
        container = client.containers.run("final_project_slave","python worker.py",network="final_project_default",environment = ["container_type=slave","container_name="+varname],detach=True, restart_policy={"Name": "on-failure"})
        countc = 0
        for _ in client.containers.list():
            countc+=1
        print(containers,countc,count,"comparisn")
        if containers+2==countc:
            flag=0
            for container in client.containers.list():
                        if '_' in container.name and flag==0:
                                print("inside if contaner")
                                container.stop()
                                #container.remove()
                                flag=1
                                
                        elif '_' in container.name and flag==1:
                            print("inside else container")
                            container.rename(varname)
                            count+=1
        else:
            for container in client.containers.list():
                if '_' in container.name:
                    print("inside for container")
                    container.rename(varname)
                    count+=1
        print("Count now",count)
        
        client.containers.prune()

def http_count():
    with counter.get_lock():
        counter.value += 1

def timer():
    global counter
    while(True):
        print("hello im here\n")
        no_of_req = counter.value
        containers =  math.ceil(no_of_req/20)
        print("number of containers needed =",containers)
        print("number of read requests = ",no_of_req)
        if containers == 0:
            containers = 1
        res1 = list_worker1()
        length = len(res1)
        #len(res1.json())
        print("length of workers are ",len(res1))
        if length>containers:
            for i in range(length-containers):
                crash_slave1()
                with counter1.get_lock(): 
                    client.containers.prune()
            res1=list_worker1()
            print("number of slaves after pruning = ",len(res1))
        elif length<containers:
            for i in range(containers-length):
                print("Containers before including orch....",client.containers.list())
                createContainer(i+length)
                print("Containers after",client.containers.list())
                print("create container now executed")
        r=list_worker1()
        print("workers now after everything",r)
        print("CONTAINERS:",length,",",containers)
        res=http_count_reset1()
        for container in client.containers.list():
            print("container_id1:",container.name)
        time.sleep(120)

@app.route('/api/v1/_count',methods=["GET"])
def http_count1():
    list1 = []
    list1.append(counter.value)
    return json.dumps(list1),200

def http_count_reset1():
    with counter.get_lock():
        counter.value = 0

@app.route('/api/v1/_count',methods=["DELETE"])
def http_count_reset():
    with counter.get_lock():
        counter.value = 0
    return {},200

@app.route('/api/v1/master/list',methods=["GET"])
def list_master():
    pid_list = []
    for container in client.containers.list():
        if "master" in container.name:
            temp=client1.inspect_container(container.id)['State']['Pid']
            pid_list.append(temp)
    return json.dumps(sorted(pid_list)),200

def list_worker1():
    pid_list = []
    for container in client.containers.list():
        if "slave" in container.name:
            temp=client1.inspect_container(container.id)['State']['Pid']
            pid_list.append(temp)
    return sorted(pid_list)

@app.route('/api/v1/worker/list',methods=["GET"])
def list_worker():
    pid_list = []
    for container in client.containers.list():
        if "slave" in container.name:
            temp=client1.inspect_container(container.id)['State']['Pid']
            pid_list.append(temp)
    return json.dumps(sorted(pid_list)),200

@app.route('/api/v1/crash/master',methods=["POST"])
def crash_master():
    slavecount=0
    for container in client.containers.list():
        if "master" in container.name:
            container.stop()
            #container.remove()
            client.containers.prune()
    for container in client.containers.list():
        if "slave" in container.name:
            slavecount+=1
        print("container_id2:",container.name)
    
    if slavecount==1:
        createContainer(0)
    return {},200


def crash_slave1():
	global flagrem	
	print("something Start\n")
	res1 = requests.get("http://localhost:8000/api/v1/worker/list")
	l = res1.json()
	print("list is = ",l)
	if(len(l)>0):
		flagrem = 1
		delete_id = l[-1]
		print("the delete id = ",delete_id)
		for container in client.containers.list():
			if client1.inspect_container(container.id)["State"]["Pid"]==delete_id:
				print("something inside\n")
				container.stop()
				#container.remove()
		#for container in client.containers.list():
			#print("container_id2:",container.name)
				break
			

@app.route('/api/v1/crash/slave',methods=["POST"])
def crash_slave():
	global flagrem	
	print("something Start\n")
	res1 = requests.get("http://localhost:8000/api/v1/worker/list")
	l = res1.json()
	print("list is = ",l)
	if(len(l)>0):
		flagrem = 1
		delete_id = l[-1]
		print("the delete id = ",delete_id)
		for container in client.containers.list():
			if client1.inspect_container(container.id)["State"]["Pid"]==delete_id:
				print("something inside\n")
				container.stop()
				#container.remove()
		#for container in client.containers.list():
			#print("container_id2:",container.name)
				break
			
	return {},200


class OrchestratorRpcClient(object):

    def __init__(self):
        self.connection = pika.BlockingConnection(
            pika.ConnectionParameters(host='rabbitmq',heartbeat=0))

        self.channel = self.connection.channel()

        result = self.channel.queue_declare(queue='')
        self.callback_queue = result.method.queue

        self.channel.basic_consume(
            queue=self.callback_queue,
            on_message_callback=self.on_response,
            auto_ack=True)

    def on_response(self, ch, method, props, body):
        if self.corr_id == props.correlation_id:
            self.response = body

    def call(self, n):
        self.response = None
        self.corr_id = str(uuid.uuid4())
        self.channel.basic_publish(
            exchange='',
            routing_key='rpc_queue',
            properties=pika.BasicProperties(
                reply_to=self.callback_queue,
                correlation_id=self.corr_id,
            ),
            body=n)
        while self.response is None:
            self.connection.process_data_events()
        return self.response


orchestrator_rpc = OrchestratorRpcClient()

def write_to_queue(queue_name,message) :
    channel.queue_declare(queue=queue_name,durable=True)
    channel.basic_publish(
        exchange='',
        routing_key=queue_name,
        body=message,
        properties=pika.BasicProperties(
            delivery_mode=2,  # make message persistent
        ))


@app.route('/api/v1/db/write', methods=["POST"])
def writetodb():
    queue_name = 'WRITE_queue'
    user_details = request.json
    if user_details['isPut']==1:
        write_message = 'INSERT INTO ' + user_details['table'] + ' VALUES(' + user_details['insert'] + ')'
        write_to_queue(queue_name,write_message)
        print("write here")
    else:
        write_message = 'DELETE FROM ' + user_details['table'] + ' WHERE  ' + user_details['column'] + '=' '"' + user_details['value'] + '"'
        write_to_queue(queue_name,write_message)
        print("write here")
    return "written"



# 9
@app.route('/api/v1/db/read', methods=["POST"])
def readfromdb():
    http_count()
    queue_name = 'READ_queue'
    user_details = dict(request.json)
    print(user_details)
    read_message = 'SELECT '+ user_details['columns'] + ' FROM ' + user_details['table'] + ' WHERE ' + user_details['where']
    print(str(user_details))
    response = orchestrator_rpc.call(json.dumps(user_details))
    return response
    
    
@app.route('/api/v1/db/clear',methods=["POST"])
def cleardb():

    queue_name = 'WRITE_queue'
    write_to_queue(queue_name,'DELETE FROM Riders')
    write_to_queue(queue_name,'DELETE FROM Ride')
    write_to_queue(queue_name,'DELETE FROM User')
    with open('/code/queries.txt','w'): pass
    return {},200
    
if __name__ == '__main__':
    
    print("check1")
    t1 = threading.Thread(target=timer, args=())
    print("check2")
    #container = client.containers.run("final_project_slave","python worker.py",links={"rabbitmq":"rabbitmq"},network="final_project_default")
    '''for i in client.containers.list() :
    	if i.name == "slave" :
    		i.stop()
    		client.containers.prune()'''
    
    #container = client.containers.run("final_project_slave","python worker.py",links={"rabbitmq":"rabbitmq"},network="final_project_default")
    t1.start()
    print("check3")
    
    #container = client.containers.run("final_project_slave","python slave.py",links={"rabbitmq":"rabbitmq"},network="final_project_default")
    app.run(debug=True,host='0.0.0.0',port=8000)
    
